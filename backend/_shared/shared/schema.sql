-- Team Management schema. Idempotent: safe to run on every Lambda cold start.
-- The data model is driven backwards from the seven organizational questions in
-- docs/DESIGN.md; team_analytics centralizes the per-team metric definitions so
-- the analytics service is a trivial rollup over a single source of truth.

-- People being tracked in the org (distinct from auth users in app_user).
CREATE TABLE IF NOT EXISTS person (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name          TEXT NOT NULL,
    location      TEXT,
    staff_type    TEXT NOT NULL CHECK (staff_type IN ('DIRECT', 'NON_DIRECT')),
    title         TEXT,
    is_org_leader BOOLEAN NOT NULL DEFAULT FALSE,
    metadata      JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Teams have a primary location; co-location (Q4) is judged against this base.
-- reports_to_id chains teams into a hierarchy and answers Q7 via the leader flag.
CREATE TABLE IF NOT EXISTS team (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name          TEXT NOT NULL,
    location      TEXT,
    description   TEXT,
    leader_id     UUID REFERENCES person(id) ON DELETE SET NULL,
    reports_to_id UUID REFERENCES person(id) ON DELETE SET NULL,
    metadata      JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- First-class membership: a person may belong to multiple teams; the leader is
-- also a member and counts toward headcount and the non-direct ratio (Q6).
CREATE TABLE IF NOT EXISTS membership (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    person_id    UUID NOT NULL REFERENCES person(id) ON DELETE CASCADE,
    team_id      UUID NOT NULL REFERENCES team(id) ON DELETE CASCADE,
    role_in_team TEXT,
    joined_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (person_id, team_id)
);

-- Monthly team achievements (Q3). month is normalized to the first of the month.
CREATE TABLE IF NOT EXISTS achievement (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    team_id     UUID NOT NULL REFERENCES team(id) ON DELETE CASCADE,
    month       DATE NOT NULL,
    title       TEXT NOT NULL,
    description TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Authentication/authorization principals, kept separate from domain people.
-- ("user" is a reserved word in PostgreSQL, so the table is named app_user.)
CREATE TABLE IF NOT EXISTS app_user (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email         TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role          TEXT NOT NULL CHECK (role IN ('ADMIN', 'MANAGER', 'CONTRIBUTOR', 'VIEWER')),
    is_active     BOOLEAN NOT NULL DEFAULT TRUE,
    token_version INTEGER NOT NULL DEFAULT 0,
    person_id     UUID REFERENCES person(id) ON DELETE SET NULL,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_membership_team ON membership(team_id);
CREATE INDEX IF NOT EXISTS idx_membership_person ON membership(person_id);
CREATE INDEX IF NOT EXISTS idx_achievement_team_month ON achievement(team_id, month);

-- Per-team metrics: one row per team, every organizational question answerable
-- from here. KPIs (analytics service) are a rollup; drill-down comes for free.
CREATE OR REPLACE VIEW team_analytics AS
SELECT
    t.id            AS team_id,
    t.name          AS team_name,
    t.location      AS team_location,
    l.id            AS leader_id,
    l.location      AS leader_location,
    l.staff_type    AS leader_staff_type,
    (l.id IS NOT NULL AND t.location IS DISTINCT FROM l.location) AS leader_not_colocated,   -- Q4
    (l.staff_type = 'NON_DIRECT')                                AS leader_is_non_direct,     -- Q5
    COUNT(m.person_id)                                           AS member_count,
    COUNT(m.person_id) FILTER (WHERE p.staff_type = 'NON_DIRECT') AS non_direct_count,
    CASE WHEN COUNT(m.person_id) > 0
         THEN COUNT(m.person_id) FILTER (WHERE p.staff_type = 'NON_DIRECT')::numeric
              / COUNT(m.person_id)
         ELSE 0 END                                              AS non_direct_ratio,         -- Q6
    (r.is_org_leader IS TRUE)                                    AS reports_to_org_leader     -- Q7
FROM team t
LEFT JOIN person     l ON l.id = t.leader_id
LEFT JOIN membership m ON m.team_id = t.id
LEFT JOIN person     p ON p.id = m.person_id
LEFT JOIN person     r ON r.id = t.reports_to_id
GROUP BY t.id, t.name, t.location, l.id, l.location, l.staff_type, r.is_org_leader;
