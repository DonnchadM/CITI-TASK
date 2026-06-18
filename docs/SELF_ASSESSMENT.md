Self Assessment:

What's implemented, known issues, and what I learned. Design rationale lives in DESIGN.md. This document checks the build against the requirements.


Overview:

A centralized team management web application that gives insight on team membership, locations, monthly achievements, leader co-location, non-direct-staff ratios, and reporting hierarchy. A single team_analytics SQL view is the source of truth for the metrics.

Stack: Python backend, PostgreSQL, React + React Responsive + Material UI frontend, AWS Serverless (S3 + CloudFront + Lambda + Aurora) via the repo's Terraform + shell scripts.

Architecture: one Lambda per resource (auth, people, teams, achievements, analytics, assistant), auto-discovered by Terraform, with cross-cutting concerns (DB access, routing, validation, response/error envelopes, JWT auth + RBAC) factored into a shared module reused by every service.

Requirements Implemented:

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

The dashboard also surfaces a quick performance overview alongside the structural KPIs: two activity cards (total achievements and achievements this month) from GET /analytics/summary, and a per-team achievement count in the breakdown table from GET /analytics/teams. This makes Q3 (monthly team achievements) visible at a glance rather than only through search, turning the dashboard into a basic read on which teams are delivering. The per-team count is joined in as a pre-aggregated subquery rather than added to the team_analytics view, so it doesn't fan out and distort the membership-based metrics.

The dashboard also adds two lightweight bar charts, achievements by team and by month, drawn with plain MUI rather than a charting library, to give a visual performance read without growing the bundle. A separate Promotions page scores each person's readiness from tenure and team achievement activity.

The seven org questions are answerable from the dashboard: four KPI cards (Q4–Q7) from GET /analytics/summary and a per-team table from GET /analytics/teams, with Q1–Q3 covered by the CRUD/search surface.

Known issues & limitations:
Aurora cold-start. Aurora Serverless v2 scales to zero, so the first request after an idle period can time out with a 500 and then succeed on retry. A non-zero min_capacity or a longer connect timeout would resolve it.

AI assistant needs a key. The assistant requires ANTHROPIC_API_KEY (set via TF_VAR_anthropic_api_key); without one it returns 503 assistant_unavailable. It runs at low effort with a capped tool-call loop to stay under CloudFront's ~30s origin timeout.

AI assistant can't reach Anthropic from the cloud, an environment constraint, not a code defect. The assistant Lambda sits in the VPC for Aurora access, but the workshop VPC gives Lambdas no internet egress (no NAT on the private subnets; public subnets get no public IP), so api.anthropic.com is unreachable and it returns 503 assistant_unreachable. It runs end-to-end locally on LocalStack with a real key. A NAT gateway, or moving the function out of the VPC, would fix it, both out of scope here.

Frontend bundle size. A single ~700 KB MUI chunk; route-level code-splitting would trim it. Functional, just not optimized.

PWA service worker is build-only. Disabled in npm run dev to avoid caching; active in production. The offline indicator still works in dev.
Testing

Backend (pytest): unit tests for the shared layer (error→HTTP mapping, validation, JWT/RBAC, PBKDF2, models), plus integration tests over the live endpoints (auth, RBAC, token revocation, referential integrity, and the analytics KPIs against a seeded org).

Frontend (Vitest + RTL + MSW): tests for permission gating, the API client (JWT inject + 401→refresh→retry), and key pages.
Both run in CI alongside the Bandit and npm audit checks.

What I learned:
Match the platform, not the textbook. The shared module started as a Lambda layer, but the participant role can't publish layers, so it failed on AWS (LocalStack hadn't enforced it). Vendoring it into each service was a low-risk fix, the app code never changed; it was always just a packaging concern.

Native deps and the Lambda runtime. bcrypt's compiled wheel wouldn't load in the runtime, so hashing moved to stdlib PBKDF2, same security, no native code. I verified each dependency in the deployed runtime rather than trusting a local import.

Centralizing cross-cutting logic pays off. With DB access, routing, validation, and JWT/RBAC in one shared module, each service was just function.py + models.py + repository.py, and whole-app fixes (like the dev proxy dropping the Authorization header) lived in one place.

One SQL view as the source of truth. Defining the per-team metrics once in team_analytics made the KPI summary a trivial rollup and gave per-team drill-down for free.
Verify in the real environment. The layer IAM block, the cold-start, and the proxy header all surfaced on deploy, not in local unit checks.
