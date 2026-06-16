# Team Management Application — Design

> Design document for the coding-workshop submission. Captures the interpretation of
> the task and the chosen approach to each feature, **before** implementation.
> Stack (per the task description): **Python** backend · **PostgreSQL** database ·
> **React + React Responsive + Material UI** frontend · AWS Serverless deployment.

## 1. Problem interpretation

The business problem is a centralized team-management tool that can answer a specific
set of organizational questions:

1. Who are the members of each team?
2. Where are the teams located?
3. What are the key achievements of each team on a monthly basis?
4. How many teams have a team leader **not co-located** with team members?
5. How many teams have a team leader who is **non-direct staff**?
6. How many teams have a **non-direct-staff-to-employees ratio above 20%**?
7. How many teams are **reporting to an organization leader**?

The design is driven **backwards from these questions** — the data model exists to make
all seven answerable, and the analytics layer answers them directly.

## 2. Data model

Entities (PostgreSQL):

```
Person
  id, name, location, staff_type [DIRECT|NON_DIRECT], title,
  is_org_leader (bool), metadata (jsonb), created_at, updated_at

Team
  id, name, location, description,
  leader_id  → Person, reports_to_id → Person (nullable),
  metadata (jsonb), created_at, updated_at

Membership                       (first-class Person ⇄ Team)
  id, person_id → Person, team_id → Team,
  role_in_team (nullable), joined_at
  UNIQUE(person_id, team_id)

Achievement
  id, team_id → Team, month (date, first-of-month),
  title, description, created_at, updated_at

User                             (authentication / access — separate from Person)
  id, email (unique), password_hash, role [ADMIN|MANAGER|CONTRIBUTOR|VIEWER],
  is_active, token_version (int), person_id → Person (nullable), created_at, updated_at
```

### Interpretation decisions

The task is deliberately underspecified in places. Naming and resolving these is part of
the design:

1. **Co-location** — A `Team` has a primary `location`; the leader is co-located ⇔
   `leader.location == team.location`. Members keep their own location (for "where are
   members"), but co-location is judged against the team's base — avoiding the ambiguous
   "any vs all members" reading.
2. **Ratio denominator** — "non-direct to employees" = `count(NON_DIRECT) / count(all members) > 0.20`.
   Denominator is full headcount.
3. **Organization leader** — explicit `Person.is_org_leader` flag; a team "reports to an org
   leader" ⇔ its `reports_to` person has `is_org_leader = true`. `reports_to_id` also chains
   teams into a hierarchy.
4. **Metadata** — JSONB on Person and Team, shape validated at the application layer
   (Pydantic model with documented known fields + `extra="allow"`): flexible but disciplined.
5. **Membership** — first-class entity; a person may belong to multiple teams; the leader is
   also a member and counts in headcount/ratio.

**User vs Person** — kept separate. Not every Person logs in, and not every User is a tracked
employee; isolating credentials from domain data is cleaner and more secure. Optional
`person_id` links a login to an employee when relevant.

## 3. Analytics — answering the org questions

A single Postgres **view** centralizes the per-team metric definitions (single source of truth);
every KPI is then a trivial rollup and per-team drill-down comes for free.

```sql
CREATE VIEW team_analytics AS
SELECT
  t.id AS team_id, t.name AS team_name, t.location AS team_location,
  l.id AS leader_id, l.location AS leader_location, l.staff_type AS leader_staff_type,
  (l.id IS NOT NULL AND t.location IS DISTINCT FROM l.location) AS leader_not_colocated,   -- Q4
  (l.staff_type = 'NON_DIRECT')                                AS leader_is_non_direct,    -- Q5
  COUNT(m.person_id)                                           AS member_count,
  COUNT(m.person_id) FILTER (WHERE p.staff_type = 'NON_DIRECT') AS non_direct_count,
  CASE WHEN COUNT(m.person_id) > 0
       THEN COUNT(m.person_id) FILTER (WHERE p.staff_type = 'NON_DIRECT')::numeric
            / COUNT(m.person_id)
       ELSE 0 END                                              AS non_direct_ratio,        -- Q6
  (r.is_org_leader IS TRUE)                                    AS reports_to_org_leader     -- Q7
FROM team t
LEFT JOIN person     l ON l.id = t.leader_id
LEFT JOIN membership m ON m.team_id = t.id
LEFT JOIN person     p ON p.id = m.person_id
LEFT JOIN person     r ON r.id = t.reports_to_id
GROUP BY t.id, t.name, t.location, l.id, l.location, l.staff_type, r.is_org_leader;
```

KPI rollup (Q4–Q7):

```sql
SELECT
  COUNT(*) FILTER (WHERE leader_not_colocated)    AS teams_leader_not_colocated,
  COUNT(*) FILTER (WHERE leader_is_non_direct)    AS teams_leader_non_direct,
  COUNT(*) FILTER (WHERE non_direct_ratio > 0.20) AS teams_high_non_direct_ratio,
  COUNT(*) FILTER (WHERE reports_to_org_leader)   AS teams_under_org_leader
FROM team_analytics;
```

Q1–Q3 are plain reads (also the CRUD/search surface): members via the `membership` join,
locations from `team`, achievements filtered by `team_id`/`month`.

Regular view (real-time, no refresh) at workshop scale; `MATERIALIZED VIEW` + index is the
documented scale-up path. Metric logic lives in the view; CRUD/validation/auth live in Python.

## 4. API contract

**Architecture:** one Lambda per resource (matches the repo's auto-discovery + CloudFront
`/api/<service>*` routing): `people`, `teams`, `achievements`, `analytics`, `auth`, `assistant`.
Shared concerns (DB access, validation, response envelope, auth middleware) are factored into a
**shared module / Lambda layer** — not copy-pasted.

CRUD convention: `POST` 201 · `GET` 200 · `GET{id}` 200/404 · `PUT` 200/400/404 · `DELETE` 204/404.

| Service | Endpoints |
|---|---|
| `people` | CRUD; list filters `?location=&staff_type=&is_org_leader=&q=&limit=&offset=`; `GET /people/{id}/teams` |
| `teams` | CRUD; `?location=&reports_to_id=&q=`. Memberships sub-resource: `GET/POST /teams/{id}/members` (409 on dup), `PUT/DELETE /teams/{id}/members/{person_id}` |
| `achievements` | CRUD; `GET` filters `?team_id=&month=&from=&to=` |
| `analytics` | read-only: `GET /analytics/summary` (Q4–Q7 + total), `GET /analytics/teams` (per-team drill-down) |
| `auth` | `POST /auth/login`, `POST /auth/refresh`, `POST /auth/logout`, `GET /auth/me`, Admin-only `…/users[/{id}]`, `PUT /auth/me/password` |
| `assistant` | `POST /assistant/query` — AI natural-language org query (read-only) |

**Status codes:** spec's 200/201/204/400/404/500 plus 401 (unauth), 403 (RBAC), 409 (conflict).

**Response shapes** (uniform, from the shared module):
- single resource returned directly; collections wrapped: `{ "data": [...], "pagination": { limit, offset, total } }`
- errors, everywhere: `{ "error": { "code", "message", "details": [ { "field", "issue" } ] } }`

`PUT` is a full update of an existing resource (404 if absent), not upsert. "Metadata CRUD" is
satisfied via the JSONB field on its parent resource.

## 5. Authentication & RBAC

- **JWT**: short-lived access token (~15 min) + refresh token (~7 days); `POST /auth/refresh`.
  Access claims: `sub, role, email, iat, exp, ver`. Role in the token → stateless authorization.
- **Revocation** via `token_version` (claim `ver` checked against the user's value): bumping it
  forces logout on password/role change or explicit logout — no token store needed.
- HS256 + server secret (RS256 = scale option). Passwords hashed with **bcrypt**.

**Permission matrix:**

| Action | Admin | Manager | Contributor | Viewer |
|---|---|---|---|---|
| Read (domain) | ✓ | ✓ | ✓ | ✓ |
| Create | ✓ | ✓ | ✓ | ✗ |
| Update | ✓ | ✓ | ✓ | ✗ |
| Delete | ✓ | ✓ | ✗ | ✗ |
| Manage users/roles | ✓ | ✗ | ✗ | ✗ |

**Enforcement** (centralized in the shared module, identical across all Lambdas):
authenticate (validate signature + `exp` + `ver` → 401), then authorize — each endpoint declares
the `(resource, action)` it needs, checked against a single declarative `PERMISSIONS` map → 403.

**Privilege-escalation safeguards:** only Admin manages users/roles; a user cannot change their own
role; role values validated against the enum; role/password change bumps `token_version`.
Only `login` and `refresh` are public; every other route requires a valid access token. A default
Admin is seeded from env-configured credentials to bootstrap user management.

## 6. Frontend information architecture

React + React Responsive + Material UI. MUI AppBar + Drawer shell (permanent on desktop,
temporary/hamburger on mobile); mobile-first.

**Routes:** `/login` (public), `/` Dashboard, `/teams` + `/teams/:id`, `/people` + `/people/:id`,
`/achievements`, `/admin/users` (Admin), `/profile`, `*`. Create/edit via MUI dialogs.

**RBAC in the UI** (spec: "hide or disable UI actions the user cannot perform"): a client-side
permission helper mirroring the backend matrix (from `/auth/me`), a `usePermissions()` hook and a
`<Can>` guard, plus `<RequireAuth>` / `<RequireRole>` route guards. **UI checks are UX only — the
backend is the real enforcement.**

**Responsive strategy:** MUI breakpoints for layout/styling; **react-responsive** for content swaps
(data table on desktop ↔ stacked cards on mobile).

**State & data:** TanStack Query for server state (caching, loading/error, optimistic updates);
lightweight AuthContext for token + user. Central API client injects the JWT, handles
401 → refresh → retry, and normalizes the error envelope. Forms via react-hook-form + yup/zod,
mirroring backend validation for instant feedback.

**Dashboard (centerpiece):** four KPI cards from `GET /analytics/summary` (the Q4–Q7 metrics) plus
a per-team analytics table from `GET /analytics/teams`. The org questions are the first thing a
reviewer sees.

**Structure:** `pages/`, `components/` (AppLayout, KpiCard, ResponsiveTable, EntityFormDialog,
ConfirmDialog, Can, FilterBar), `services/` (apiClient + per-resource modules), `hooks/`,
`context/`, `theme/`, `routes/`.

## 7. Progressive Web App

Via `vite-plugin-pwa` / Workbox: Web App Manifest (installable); service worker precaches the app
shell (offline load); read GETs cached NetworkFirst (offline shows last-known data), mutations
network-only; online/offline indicator that disables saves when offline; update-available prompt;
API caches cleared on logout.

## 8. AI integration — natural-language org query

An "Ask the org" box where a user asks questions in natural language and gets a grounded answer
from live data.

- **Architecture: Claude tool use over the existing API** (not text-to-SQL). Claude interprets the
  question, calls read-only tools that mirror our analytics/list endpoints, we execute them against
  the locked data surface, and Claude composes the answer. Safe (constrained, parameterized, no
  writes), reuses what we built, and demonstrates modern AI-engineering.
- A dedicated **`assistant`** backend service (`POST /assistant/query {question}` → `{answer, data?}`)
  keeps the Anthropic API key server-side.
- Model `claude-opus-4-8` (adaptive thinking) via the official Anthropic Python SDK tool runner.
  Tools: `get_kpi_summary`, `get_team_analytics`, `list_teams`, `get_team_members`,
  `get_achievements`, `list_people`.
- Grounding: answers only from tool results; respects the caller's read permissions; key from env
  locally / Secrets Manager in cloud.

## 9. Validation, error handling, testing

**Validation** — Pydantic v2 (`*Create/*Update/*Out` per resource), four layers: schema
(types/required/enums/formats) → 400; referential (referenced entities exist; DB FK as safety net);
business rules (role enum, no self-escalation, month normalization); uniqueness (email,
`UNIQUE(person, team)`) → 409. Frontend yup/zod mirrors these for UX; backend stays source of truth.

**Error handling** — exception hierarchy → HTTP mapping in the shared module
(`ValidationError`→400, `NotFoundError`→404, `ConflictError`→409, `Unauthenticated`→401,
`Forbidden`→403, unexpected→500 with a generic message, internals logged not leaked). A handler
wrapper serializes any error to the consistent envelope. All writes are transactional (rollback on
error). Structured logging with a per-request correlation id.

**Testing** (targets: BE 80% / FE 80% / API 90% / errors 90% / critical E2E 100%):
- Backend unit (pytest): schemas, permission matrix, business rules, exception mapping.
- Backend integration: invoke `handler(event, ctx)` against a test Postgres, each test in a
  rolled-back transaction; cover CRUD + every error status; dedicated `team_analytics` tests
  asserting Q4–Q7 against seeded orgs.
- Frontend: Jest + React Testing Library (components), MSW (API integration).
- E2E: Cypress — login→dashboard, role-gated CRUD, RBAC visibility, membership add/remove.
- CI: add pytest + Jest jobs alongside the existing Bandit / npm-audit / Checkov scanners.

## 10. Deployment

AWS Serverless via the repo's Terraform + shell scripts (S3 + CloudFront + Lambda + Aurora
PostgreSQL), using the existing auto-discovery so each backend service deploys as its own Lambda.
Detailed deployment work is sequenced after the core application is built and tested locally.
