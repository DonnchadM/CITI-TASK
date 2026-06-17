# Team Management Application

A centralized team-management web app built for the Citi coding workshop. It stores an
organization's people, teams, memberships, and monthly achievements, and answers a specific set
of organizational questions through an analytics dashboard — plus a natural-language **"Ask the
org"** assistant.

The whole design is driven backwards from the seven questions the business needs to answer:

1. Who are the members of each team?
2. Where are the teams located?
3. What are the key achievements of each team on a monthly basis?
4. How many teams have a team leader **not co-located** with team members?
5. How many teams have a team leader who is **non-direct staff**?
6. How many teams have a **non-direct-staff-to-employees ratio above 20%**?
7. How many teams are **reporting to an organization leader**?

Q1–Q3 are served by the CRUD + search surface; Q4–Q7 are KPI cards on the dashboard, computed by
a single PostgreSQL view (`team_analytics`) that is the source of truth for every metric.

> **Design rationale:** [docs/DESIGN.md](docs/DESIGN.md) · **Self-assessment (requirements,
> known issues, learnings):** [docs/SELF_ASSESSMENT.md](docs/SELF_ASSESSMENT.md) ·
> **Workshop brief:** [docs/README.md](docs/README.md)

## Architecture

| Layer | Choice |
|---|---|
| **Backend** | Python 3.11, **one Lambda per resource** (`auth`, `people`, `teams`, `achievements`, `analytics`, `assistant`), auto-discovered by Terraform and exposed through Lambda Function URLs |
| **Shared code** | A shared module (DB access, HTTP routing, response envelope, validation, JWT/RBAC) lives once in `backend/_shared/shared` and is vendored into each service at build time |
| **Database** | PostgreSQL (local 16; AWS Aurora Serverless v2 in the cloud); the `team_analytics` SQL view centralizes the KPI definitions |
| **Frontend** | React 19 + Material UI + React Responsive, TanStack Query, react-hook-form + zod; a PWA (installable, offline-capable) |
| **AI assistant** | Claude (`claude-opus-4-8`) tool-use over read-only data tools — not text-to-SQL |
| **Routing** | CloudFront serves the SPA from S3 and routes `/api/<service>*` to each service's Lambda |

```
Browser ── CloudFront ──┬── S3 (React SPA)
                        └── /api/<service> ── Lambda (auth│people│teams│achievements│analytics│assistant) ── Aurora PostgreSQL
```

## Run locally

The repo ships a one-command local environment (PostgreSQL, LocalStack, the Lambdas via
Terraform, and the React dev server):

```sh
source ~/.bashrc
./bin/start-dev.sh
```

This starts the backend services on **LocalStack** — reachable through the CORS proxy at
`http://localhost:3001` — and the **frontend** dev server (Vite); open the URL it prints.

A default admin is seeded on first run from `ADMIN_EMAIL` / `ADMIN_PASSWORD`. Locally that is:

```
email:    admin@coding-workshop.local
password: ChangeMe123!
```

The frontend points at the backend via `VITE_API_URL` (defaults to `http://localhost:3001`; see
[frontend/.env.sample](frontend/.env.sample)).

## Deploy to AWS

Deployment uses the repo's Terraform + scripts (S3 + CloudFront + Lambda + Aurora). From the VDI,
with your participant environment configured:

```sh
./bin/deploy-backend.sh aws     # Aurora + the six Lambdas + CloudFront API routes
./bin/deploy-frontend.sh aws    # build the SPA and publish to S3 / CloudFront
```

**Secrets are injected as Terraform variables** (never committed) — set them in your shell before
deploying:

| Variable | Purpose |
|---|---|
| `TF_VAR_jwt_secret` | HS256 signing secret for JWTs |
| `TF_VAR_admin_password` | bootstrap admin password (use a strong value on AWS) |
| `TF_VAR_anthropic_api_key` | Anthropic API key for the assistant (empty ⇒ assistant returns `503 assistant_unavailable`) |

> **Note on the cloud assistant:** the workshop VPC provides no outbound internet egress for
> Lambdas, so the assistant cannot reach `api.anthropic.com` from this particular deployment and
> degrades gracefully to `503 assistant_unreachable`. It is fully functional locally (LocalStack
> has egress). See [docs/SELF_ASSESSMENT.md](docs/SELF_ASSESSMENT.md) for the diagnosis and
> remediation options.

## API reference

All endpoints are under `/api`. Every route except `POST /auth/login` and `POST /auth/refresh`
requires an `Authorization: Bearer <access_token>` header.

**Conventions:** `POST`→201 · `GET`→200 · `PUT`→200 (404 if absent) · `DELETE`→204 ·
validation→400 · auth→401 · RBAC→403 · not found→404 · conflict→409 · server→500.
Single resources are returned directly; collections are wrapped as
`{ "data": [...], "pagination": { "limit", "offset", "total" } }`; errors are always
`{ "error": { "code", "message", "details": [...] } }`.

| Service | Endpoints |
|---|---|
| `auth` | `POST /auth/login`, `POST /auth/refresh`, `POST /auth/logout`, `GET /auth/me`, `PUT /auth/me/password`; Admin-only `GET/POST /auth/users`, `GET/PUT/DELETE /auth/users/{id}` |
| `people` | CRUD `/people[/{id}]`; list filters `?q=&location=&staff_type=&is_org_leader=&limit=&offset=`; `GET /people/{id}/teams` |
| `teams` | CRUD `/teams[/{id}]`; filters `?q=&location=&reports_to_id=`; memberships: `GET/POST /teams/{id}/members` (409 on duplicate), `PUT/DELETE /teams/{id}/members/{person_id}` |
| `achievements` | CRUD `/achievements[/{id}]`; filters `?team_id=&month=&from=&to=` |
| `analytics` | `GET /analytics/summary` (Q4–Q7 KPIs + total teams), `GET /analytics/teams` (per-team drill-down) |
| `assistant` | `POST /assistant/query` `{ "question": "..." }` → `{ "answer", "data" }` (read-only, AI) |

**Example:**

```sh
# Log in, then read the org KPIs
TOKEN=$(curl -s -X POST http://localhost:3001/api/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"admin@coding-workshop.local","password":"ChangeMe123!"}' \
  | python3 -c "import sys,json;print(json.load(sys.stdin)['access_token'])")

curl -s http://localhost:3001/api/analytics/summary -H "Authorization: Bearer $TOKEN"
# { "total_teams": 4, "teams_leader_not_colocated": 2, "teams_leader_non_direct": 1,
#   "teams_high_non_direct_ratio": 2, "teams_under_org_leader": 2 }
```

## Authentication & roles

JWT (HS256) access + refresh tokens; passwords hashed with PBKDF2-HMAC-SHA256; revocation via a
per-user `token_version`. Authorization is a declarative permission matrix enforced centrally in
the shared module (and mirrored in the UI for show/hide — the backend is the real gate):

| Action | Admin | Manager | Contributor | Viewer |
|---|:--:|:--:|:--:|:--:|
| Read | ✓ | ✓ | ✓ | ✓ |
| Create / Update | ✓ | ✓ | ✓ | ✗ |
| Delete | ✓ | ✓ | ✗ | ✗ |
| Manage users / roles | ✓ | ✗ | ✗ | ✗ |

## Testing

```sh
# Backend — pytest (shared-layer units + HTTP-integration)
cd backend/tests && pip install -r requirements.txt && python -m pytest

# Frontend — Vitest + React Testing Library + MSW
cd frontend && npm test
```

Both suites also run in CI ([.github/workflows](.github/workflows)) alongside the Bandit and
`npm audit` security checks. See [docs/SELF_ASSESSMENT.md](docs/SELF_ASSESSMENT.md) for coverage
details.

## Repository layout

```
backend/        one folder per Lambda service (+ _shared/shared, tests/)
frontend/       React + MUI SPA (PWA)
infra/          Terraform (Lambda, Aurora, S3, CloudFront, IAM)
bin/            start-dev / deploy / setup scripts
docs/           DESIGN.md, SELF_ASSESSMENT.md, and the workshop guides
```

## Contributing

See the [CONTRIBUTING](./CONTRIBUTING.md) resource for more details.

## License

See the [LICENSE](./LICENSE) resource for more details.

## Security

See the
[Security Issue Notifications](./CONTRIBUTING.md#security-issue-notifications)
resource for more details.

## Authors

This application was built on the workshop scaffold created by:

* Colin Heilman - [@heilmancs](https://github.com/heilmancs)
* Eugene Istrati - [@eistrati](https://github.com/eistrati)
* Isaiah Cornelius Smith - [@corneliusmith](https://github.com/corneliusmith)
* Juan Arevalo - [@jparevalo27](https://github.com/jparevalo27)
* Michael Annucci - [@michael-annucci](https://github.com/michael-annucci)
