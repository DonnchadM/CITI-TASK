"""Read-only tools the assistant may call.

Each tool mirrors a piece of our analytics/list surface and runs a parameterized,
read-only query against the locked data model via shared.db. Claude calls these;
we execute them and feed the results back. No writes, no arbitrary SQL — the
assistant can only see what these tools expose.
"""

import json
from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from shared.db import transaction

_LIMIT = 200

# Tool schemas advertised to Claude (Anthropic tool-use `input_schema` format).
TOOLS = [
    {
        "name": "get_kpi_summary",
        "description": "Org-wide KPI rollup: total teams, plus counts of teams whose leader is "
                       "not co-located, whose leader is non-direct staff, with a non-direct ratio "
                       "above 20%, and that report to an organization leader.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "get_team_analytics",
        "description": "Per-team metrics (location, leader, member count, non-direct ratio, and the "
                       "co-location / non-direct-leader / reports-to-org-leader flags).",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "list_teams",
        "description": "List teams, optionally filtered by a name search or location.",
        "input_schema": {
            "type": "object",
            "properties": {
                "q": {"type": "string", "description": "Case-insensitive name search"},
                "location": {"type": "string"},
            },
        },
    },
    {
        "name": "get_team_members",
        "description": "List the members of a team given its id (from list_teams or get_team_analytics).",
        "input_schema": {
            "type": "object",
            "properties": {"team_id": {"type": "string", "description": "Team UUID"}},
            "required": ["team_id"],
        },
    },
    {
        "name": "get_achievements",
        "description": "List monthly team achievements, optionally filtered by team id or month (YYYY-MM).",
        "input_schema": {
            "type": "object",
            "properties": {
                "team_id": {"type": "string"},
                "month": {"type": "string", "description": "Month as YYYY-MM"},
            },
        },
    },
    {
        "name": "list_people",
        "description": "List people, optionally filtered by name search, staff_type (DIRECT/NON_DIRECT), "
                       "location, or org-leader status.",
        "input_schema": {
            "type": "object",
            "properties": {
                "q": {"type": "string"},
                "staff_type": {"type": "string", "enum": ["DIRECT", "NON_DIRECT"]},
                "location": {"type": "string"},
                "is_org_leader": {"type": "boolean"},
            },
        },
    },
]


def _rows(sql: str, params=None) -> list:
    with transaction() as cur:
        cur.execute(sql, params or [])  # nosec B608 - static SQL, parameterized values
        return cur.fetchall()


def _get_kpi_summary(_args) -> dict:
    return _rows(
        "SELECT COUNT(*) AS total_teams, "
        "COUNT(*) FILTER (WHERE leader_not_colocated) AS teams_leader_not_colocated, "
        "COUNT(*) FILTER (WHERE leader_is_non_direct) AS teams_leader_non_direct, "
        "COUNT(*) FILTER (WHERE non_direct_ratio > 0.20) AS teams_high_non_direct_ratio, "
        "COUNT(*) FILTER (WHERE reports_to_org_leader) AS teams_under_org_leader "
        "FROM team_analytics"
    )[0]


def _get_team_analytics(_args) -> list:
    return _rows(
        "SELECT team_name, team_location, leader_location, leader_staff_type, member_count, "
        "non_direct_count, non_direct_ratio, leader_not_colocated, leader_is_non_direct, "
        "reports_to_org_leader FROM team_analytics ORDER BY team_name"
    )


def _list_teams(args) -> list:
    where, params = [], []
    if args.get("q"):
        where.append("name ILIKE %s")
        params.append(f"%{args['q']}%")
    if args.get("location"):
        where.append("location = %s")
        params.append(args["location"])
    clause = f"WHERE {' AND '.join(where)}" if where else ""
    return _rows(
        f"SELECT id, name, location, description FROM team {clause} ORDER BY name LIMIT {_LIMIT}",  # nosec B608 - clause from fixed fragments
        params,
    )


def _get_team_members(args) -> list:
    return _rows(
        "SELECT p.name, p.location, p.staff_type, m.role_in_team "
        "FROM membership m JOIN person p ON p.id = m.person_id "
        "WHERE m.team_id = %s ORDER BY p.name",
        [args["team_id"]],
    )


def _get_achievements(args) -> list:
    where, params = [], []
    if args.get("team_id"):
        where.append("a.team_id = %s")
        params.append(args["team_id"])
    if args.get("month"):
        where.append("a.month = %s")
        params.append(f"{args['month']}-01")
    clause = f"WHERE {' AND '.join(where)}" if where else ""
    return _rows(
        f"SELECT t.name AS team, a.month, a.title, a.description FROM achievement a "  # nosec B608 - clause from fixed fragments
        f"JOIN team t ON t.id = a.team_id {clause} ORDER BY a.month DESC LIMIT {_LIMIT}",
        params,
    )


def _list_people(args) -> list:
    where, params = [], []
    if args.get("q"):
        where.append("(name ILIKE %s OR title ILIKE %s)")
        params += [f"%{args['q']}%", f"%{args['q']}%"]
    if args.get("staff_type"):
        where.append("staff_type = %s")
        params.append(args["staff_type"])
    if args.get("location"):
        where.append("location = %s")
        params.append(args["location"])
    if args.get("is_org_leader") is not None:
        where.append("is_org_leader = %s")
        params.append(args["is_org_leader"])
    clause = f"WHERE {' AND '.join(where)}" if where else ""
    return _rows(
        f"SELECT name, location, staff_type, title, is_org_leader FROM person {clause} "  # nosec B608 - clause from fixed fragments
        f"ORDER BY name LIMIT {_LIMIT}",
        params,
    )


_DISPATCH = {
    "get_kpi_summary": _get_kpi_summary,
    "get_team_analytics": _get_team_analytics,
    "list_teams": _list_teams,
    "get_team_members": _get_team_members,
    "get_achievements": _get_achievements,
    "list_people": _list_people,
}


def _json_default(value: Any):
    if isinstance(value, (UUID, datetime, date)):
        return str(value)
    if isinstance(value, Decimal):
        return float(value)
    raise TypeError(f"Not JSON serializable: {type(value)}")


def run_tool(name: str, args: dict) -> str:
    """Execute a read-only tool and return its result as a JSON string."""
    handler = _DISPATCH.get(name)
    if handler is None:
        return json.dumps({"error": f"Unknown tool: {name}"})
    return json.dumps(handler(args or {}), default=_json_default)
