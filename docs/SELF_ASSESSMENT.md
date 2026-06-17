# Self-Assessment

A candid review of the Team Management submission: what's implemented, what the
known issues are, and what I learned. The design rationale lives in
[DESIGN.md](./DESIGN.md); this document grades the build against the requirements.

## Overview

A centralized team-management web application, built to answer seven
organizational questions (team membership, locations, monthly achievements,
leader co-location, non-direct-staff ratios, and reporting hierarchy). The design
is driven backwards from those questions — the data model exists to make them
answerable, and a single `team_analytics` SQL view is the source of truth for the
metrics.

**Stack (as required):** Python backend · PostgreSQL · React + React Responsive +
Material UI frontend · AWS Serverless (S3 + CloudFront + Lambda + Aurora) via the
repo's Terraform + shell scripts.

**Architecture:** one Lambda per resource (`auth`, `people`, `teams`,
`achievements`, `analytics`, `assistant`), auto-discovered by Terraform, with
cross-cutting concerns (DB access, routing, validation, response/error envelopes,
JWT auth + RBAC) factored into a shared module reused by every service.

## Requirements implemented

| Requirement (from the workshop brief) | Status | Where |
|---|---|---|
| Store & manage data (PostgreSQL) | ✅ | `person`, `team`, `membership`, `achievement`, `app_user` tables ([schema.sql](../backend/_shared/shared/schema.sql)) |
| CRUD for individuals, teams, achievements | ✅ | `people`, `teams`, `achievements` services |
| Individual- & team-level metadata | ✅ | JSONB `metadata` on `person` and `team`, validated via Pydantic (`extra="allow"`) |
| Search & filter | ✅ | List filters: `?q=`, `?location=`, `?staff_type=`, `?is_org_leader=`, `?team_id=`, `?month=`, `?from=`, `?to=` |
| Authentication (JWT, password hashing, expiry/refresh) | ✅ | `auth` service: JWT HS256, access + refresh tokens, PBKDF2 hashing, `token_version` revocation |
| RBAC (4 roles, restrict endpoints, prevent escalation) | ✅ | Declarative permission matrix in the shared module; safeguards (no self-role-change, no self-delete, admin-only user management) |
| RESTful API, correct status codes, consistent JSON | ✅ | 200/201/204/400/401/403/404/409/500; uniform `{data, pagination}` / `{error:{code,message,details}}` envelopes |
| Validation with meaningful errors | ✅ | Pydantic v2 schemas → 400 with field-level `details`; referential checks → 400; uniqueness → 409 |
| Error handling (consistent, no leaks, no inconsistent state) | ✅ | Exception hierarchy → HTTP mapping; transactional writes (rollback on error); generic 500 message with internals logged |
| Responsive React + MUI frontend | ✅ | MUI AppBar + responsive Drawer; `react-responsive` swaps tables ↔ cards on mobile |
| Frontend state, feedback, loading states | ✅ | TanStack Query (caching, loading/error states); disabled inputs while submitting |
| Hide/disable UI actions the user can't perform | ✅ | `usePermissions()` + `<Can>` mirror the backend matrix (UX only; backend enforces) |
| PWA capabilities | ✅ | `vite-plugin-pwa`: installable manifest, service-worker app-shell precache, NetworkFirst API caching, offline indicator, update prompt |
| Intelligent / AI features | ✅ | `assistant` service: Claude tool-use over read-only endpoints ("Ask the org") |
| Deploy to AWS Serverless | ✅ | Backend (Aurora + Lambdas) and frontend (S3 + CloudFront) deployed and verified live |

The seven organizational questions are answerable from the dashboard: four KPI
cards (Q4–Q7) from `GET /analytics/summary` and a per-team table from
`GET /analytics/teams`, with Q1–Q3 covered by the CRUD/search surface.

## Known issues & limitations

- **Aurora cold-start.** Aurora Serverless v2 is configured to scale to zero, so
  the first request after an idle period can time out and return a 500 (the
  15-second DB connect timeout is shorter than a cold resume); it succeeds on
  retry. Mitigations would be a non-zero `min_capacity` (higher cost) or a longer
  connect timeout / connect-retry.
- **AI assistant requires a key.** The `assistant` service needs an
  `ANTHROPIC_API_KEY` (injected via `TF_VAR_anthropic_api_key`). Without one it
  degrades gracefully to a `503 assistant_unavailable`. Long answers also approach
  CloudFront's ~30s origin timeout, so the model runs at low effort with a capped
  tool-call loop.
- **AI assistant cannot reach Anthropic from the cloud (network constraint, not a
  code defect).** The `assistant` Lambda runs inside the VPC because it needs
  in-VPC access to Aurora. The workshop VPC provides no internet egress for
  Lambdas: public subnets give a Lambda no public IP, and the private subnets have
  no NAT gateway — verified directly, their route tables carry only a `local` route
  plus S3/interface VPC endpoints, with no `0.0.0.0/0` to the internet. So
  `api.anthropic.com` is unreachable and the call fails with the SDK's
  `APIConnectionError` ("Connection error") after its retry/backoff (~18s, visible
  in CloudWatch — the request never leaves the VPC, so nothing appears in the
  Anthropic console). The service is fully functional on LocalStack (Docker has
  egress) and verified end-to-end there with a real key. It would work in the cloud
  with any Lambda internet path — a NAT gateway on the private subnets, or moving
  the function out of the VPC and reaching data over the public Function URLs
  instead of a direct DB connection. Both were judged out of scope for this
  submission (NAT adds cost and is likely outside the participant role's
  permissions; the out-of-VPC rework is a design change for an optional feature).
- **Frontend bundle size.** The production bundle is a single ~700 KB chunk (MUI);
  route-level code-splitting would reduce it. Functional, not yet optimized.
- **PWA service worker is build-only.** It's disabled in `npm run dev` (to avoid
  caching during development) and active in production builds; the offline
  *indicator* works in dev.

## Testing

- **Backend** — `pytest` suite under [backend/tests/](../backend/tests): unit tests
  for the shared layer (error→HTTP mapping, request parsing/validation, JWT + RBAC,
  PBKDF2, Pydantic models) plus HTTP-integration tests that exercise the live
  endpoints (auth flow, RBAC enforcement, token revocation, referential integrity,
  and the analytics KPIs asserted against a crafted org).
- **Frontend** — Vitest + React Testing Library + MSW (Vite-native, chosen over
  Jest to share the build pipeline): component/behaviour tests for the permission
  gating, API client (JWT inject + 401→refresh→retry), and key pages.
- Both suites run in CI ([.github/workflows](../.github/workflows)) alongside the
  Bandit / `npm audit` security checks.

## What I learned

- **Match the platform, not the textbook.** The "shared module" was first built as
  a Lambda layer — clean and design-faithful — but the workshop's participant IAM
  role isn't granted `lambda:PublishLayerVersion`, so it failed on real AWS
  (LocalStack hadn't enforced it). Switching to vendoring the shared module into
  each service's own package was a small, low-risk change because the application
  code (`from shared import ...`) never changed — the mechanism was always a
  packaging concern, not an application one.
- **Native dependencies and the Lambda runtime.** `bcrypt`'s compiled wheel is
  tied to the build host's glibc and wouldn't load in the older Lambda runtime, so
  password hashing moved to stdlib PBKDF2-HMAC-SHA256 — no native code, identical
  security properties, loads everywhere. `psycopg[binary]`, `pydantic_core`, and
  the Anthropic SDK's `jiter` ship portable wheels and were fine; I verified each
  in the deployed runtime rather than trusting a local import.
- **Centralizing cross-cutting logic pays off.** Putting DB access, routing, the
  response envelope, validation, and JWT/RBAC in one shared module meant each new
  service was just `function.py` + `models.py` + `repository.py` — consistent,
  and the fix for a whole-app concern (e.g. the dev proxy dropping the
  `Authorization` header) lived in one place.
- **The SQL view as a single source of truth.** Defining the per-team metrics once
  in `team_analytics` made the KPI summary a trivial rollup and gave per-team
  drill-down for free, keeping the metric definitions out of (and consistent
  across) the Python and the UI.
- **Verify in the real environment.** Several issues (the layer IAM block, the
  Aurora cold-start, the proxy header) only surfaced on deploy/integration, not in
  local unit-level checks — end-to-end verification caught what isolated tests
  would have missed.
