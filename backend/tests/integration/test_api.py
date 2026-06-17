"""Integration tests against the running local stack (LocalStack via the :3001 proxy).

These create their own data with unique names and clean up, so they're robust to
whatever is already in the dev database. They auto-skip when the stack is down.
"""

import uuid

import pytest


def uniq(prefix):
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


# --- auth + RBAC -------------------------------------------------------------

def test_login_rejects_bad_password(http):
    status, body = http("POST", "/auth/login", body={"email": "admin@coding-workshop.local", "password": "nope"})
    assert status == 401
    assert body["error"]["code"] == "unauthenticated"


def test_me_and_refresh(http, admin_token):
    status, me = http("GET", "/auth/me", token=admin_token)
    assert status == 200 and me["role"] == "ADMIN"


def test_protected_route_requires_token(http):
    status, _ = http("GET", "/people")
    assert status == 401


def test_viewer_cannot_create(http, admin_token):
    email = f"{uniq('viewer')}@x.io"
    status, _ = http("POST", "/auth/users", token=admin_token,
                     body={"email": email, "password": "viewerpass1", "role": "VIEWER"})
    assert status == 201
    _, login = http("POST", "/auth/login", body={"email": email, "password": "viewerpass1"})
    vtoken = login["access_token"]
    status, body = http("POST", "/people", token=vtoken,
                        body={"name": "X", "staff_type": "DIRECT"})
    assert status == 403 and body["error"]["code"] == "forbidden"


# --- people CRUD + validation ------------------------------------------------

def test_people_crud_lifecycle(http, admin_token):
    name = uniq("Person")
    status, created = http("POST", "/people", token=admin_token,
                           body={"name": name, "location": "London", "staff_type": "DIRECT"})
    assert status == 201
    pid = created["id"]
    try:
        status, got = http("GET", f"/people/{pid}", token=admin_token)
        assert status == 200 and got["name"] == name

        status, listed = http("GET", "/people?limit=200", token=admin_token)
        assert status == 200 and "pagination" in listed

        status, updated = http("PUT", f"/people/{pid}", token=admin_token,
                               body={"name": name, "location": "Paris", "staff_type": "NON_DIRECT"})
        assert status == 200 and updated["location"] == "Paris"
    finally:
        status, _ = http("DELETE", f"/people/{pid}", token=admin_token)
        assert status == 204
    assert http("GET", f"/people/{pid}", token=admin_token)[0] == 404


def test_people_validation_and_missing(http, admin_token):
    status, body = http("POST", "/people", token=admin_token, body={"staff_type": "DIRECT"})
    assert status == 400 and body["error"]["details"]
    assert http("GET", "/people/00000000-0000-0000-0000-000000000000", token=admin_token)[0] == 404
    assert http("GET", "/people/not-a-uuid", token=admin_token)[0] == 404


# --- teams + memberships -----------------------------------------------------

def test_team_membership_flow_and_referential(http, admin_token):
    _, leader = http("POST", "/people", token=admin_token,
                     body={"name": uniq("Leader"), "location": "London", "staff_type": "DIRECT"})
    _, team = http("POST", "/teams", token=admin_token,
                   body={"name": uniq("Team"), "location": "London", "leader_id": leader["id"]})
    tid, pid = team["id"], leader["id"]
    try:
        status, _ = http("POST", f"/teams/{tid}/members", token=admin_token, body={"person_id": pid})
        assert status == 201
        # duplicate membership -> 409
        assert http("POST", f"/teams/{tid}/members", token=admin_token, body={"person_id": pid})[0] == 409
        # referential: non-existent leader -> 400
        assert http("POST", "/teams", token=admin_token,
                    body={"name": uniq("Bad"), "leader_id": "00000000-0000-0000-0000-000000000000"})[0] == 400
        assert http("DELETE", f"/teams/{tid}/members/{pid}", token=admin_token)[0] == 204
    finally:
        http("DELETE", f"/teams/{tid}", token=admin_token)
        http("DELETE", f"/people/{pid}", token=admin_token)


# --- achievements ------------------------------------------------------------

def test_achievement_month_normalized_and_referential(http, admin_token):
    _, team = http("POST", "/teams", token=admin_token, body={"name": uniq("AchTeam")})
    tid = team["id"]
    try:
        status, ach = http("POST", "/achievements", token=admin_token,
                           body={"team_id": tid, "month": "2026-06-15", "title": uniq("win")})
        assert status == 201 and ach["month"] == "2026-06-01"
        http("DELETE", f"/achievements/{ach['id']}", token=admin_token)
        assert http("POST", "/achievements", token=admin_token,
                    body={"team_id": "00000000-0000-0000-0000-000000000000",
                          "month": "2026-06-01", "title": "x"})[0] == 400
    finally:
        http("DELETE", f"/teams/{tid}", token=admin_token)


# --- analytics (the org-question metrics) ------------------------------------

def test_analytics_summary_shape(http, admin_token):
    status, summary = http("GET", "/analytics/summary", token=admin_token)
    assert status == 200
    for key in ("total_teams", "teams_leader_not_colocated", "teams_leader_non_direct",
                "teams_high_non_direct_ratio", "teams_under_org_leader"):
        assert isinstance(summary[key], int)


def test_analytics_flags_a_non_colocated_leader(http, admin_token):
    # Leader in Paris, team based in London -> the team must be flagged not co-located (Q4).
    _, leader = http("POST", "/people", token=admin_token,
                     body={"name": uniq("RemoteLead"), "location": "Paris", "staff_type": "DIRECT"})
    _, team = http("POST", "/teams", token=admin_token,
                   body={"name": uniq("Distributed"), "location": "London", "leader_id": leader["id"]})
    tid, pid = team["id"], leader["id"]
    try:
        status, rows = http("GET", "/analytics/teams", token=admin_token)
        assert status == 200
        row = next(r for r in rows["data"] if r["team_id"] == tid)
        assert row["leader_not_colocated"] is True
        assert row["team_location"] == "London" and row["leader_location"] == "Paris"
    finally:
        http("DELETE", f"/teams/{tid}", token=admin_token)
        http("DELETE", f"/people/{pid}", token=admin_token)


# --- assistant (no real model call: auth + validation only) ------------------

def test_assistant_requires_auth(http):
    assert http("POST", "/assistant/query", body={"question": "hi"})[0] == 401


def test_assistant_validates_empty_question(http, admin_token):
    # validation runs before any model call, so this never hits Anthropic
    assert http("POST", "/assistant/query", token=admin_token, body={"question": ""})[0] == 400
