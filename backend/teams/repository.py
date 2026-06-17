"""SQL data access for teams and their memberships.

Foreign keys to person (leader, reports-to, member) are checked for existence
before a write so the caller gets a clear 400 rather than a raw FK error; the
database FK remains the ultimate safety net.
"""

from typing import List, Optional, Tuple

import psycopg
from psycopg.types.json import Json

from shared.db import transaction
from shared.errors import ConflictError, NotFoundError, ValidationError
from shared.http import path_uuid

_COLUMNS = (
    "id, name, location, description, leader_id, reports_to_id, "
    "metadata, created_at, updated_at"
)


def _check_person(cur, person_id, field: str) -> None:
    """Raise 400 if a referenced person id is given but does not exist."""
    if person_id is None:
        return
    cur.execute("SELECT 1 FROM person WHERE id = %s", [person_id])
    if cur.fetchone() is None:
        raise ValidationError(
            "A referenced person does not exist.",
            details=[{"field": field, "issue": "no person with that id"}],
        )


def _require_team(cur, team_id) -> None:
    cur.execute("SELECT 1 FROM team WHERE id = %s", [team_id])
    if cur.fetchone() is None:
        raise NotFoundError("Team not found.")


def list_teams(filters: dict, limit: int, offset: int) -> Tuple[List[dict], int]:
    where: List[str] = []
    params: List[object] = []
    if filters.get("location"):
        where.append("location = %s")
        params.append(filters["location"])
    if filters.get("reports_to_id"):
        where.append("reports_to_id = %s")
        params.append(filters["reports_to_id"])
    if filters.get("q"):
        where.append("name ILIKE %s")
        params.append(f"%{filters['q']}%")

    clause = f"WHERE {' AND '.join(where)}" if where else ""
    with transaction() as cur:
        cur.execute(f"SELECT COUNT(*) AS total FROM team {clause}", params)  # nosec B608 - parameterized query; only code-controlled identifiers are interpolated
        total = cur.fetchone()["total"]
        cur.execute(
            f"SELECT {_COLUMNS} FROM team {clause} "  # nosec B608 - parameterized query; only code-controlled identifiers are interpolated
            f"ORDER BY created_at DESC, id LIMIT %s OFFSET %s",
            [*params, limit, offset],
        )
        return cur.fetchall(), total


def get_team(team_id: str) -> dict:
    with transaction() as cur:
        cur.execute(f"SELECT {_COLUMNS} FROM team WHERE id = %s", [path_uuid(team_id)])  # nosec B608 - parameterized query; only code-controlled identifiers are interpolated
        row = cur.fetchone()
    if row is None:
        raise NotFoundError("Team not found.")
    return row


def create_team(data: dict) -> dict:
    with transaction() as cur:
        _check_person(cur, data["leader_id"], "leader_id")
        _check_person(cur, data["reports_to_id"], "reports_to_id")
        cur.execute(
            f"INSERT INTO team (name, location, description, leader_id, reports_to_id, metadata) "  # nosec B608 - parameterized query; only code-controlled identifiers are interpolated
            f"VALUES (%s, %s, %s, %s, %s, %s) RETURNING {_COLUMNS}",
            [
                data["name"],
                data["location"],
                data["description"],
                data["leader_id"],
                data["reports_to_id"],
                Json(data["metadata"]),
            ],
        )
        return cur.fetchone()


def update_team(team_id: str, data: dict) -> dict:
    with transaction() as cur:
        _check_person(cur, data["leader_id"], "leader_id")
        _check_person(cur, data["reports_to_id"], "reports_to_id")
        cur.execute(
            f"UPDATE team SET name = %s, location = %s, description = %s, leader_id = %s, "  # nosec B608 - parameterized query; only code-controlled identifiers are interpolated
            f"reports_to_id = %s, metadata = %s, updated_at = now() "
            f"WHERE id = %s RETURNING {_COLUMNS}",
            [
                data["name"],
                data["location"],
                data["description"],
                data["leader_id"],
                data["reports_to_id"],
                Json(data["metadata"]),
                path_uuid(team_id),
            ],
        )
        row = cur.fetchone()
    if row is None:
        raise NotFoundError("Team not found.")
    return row


def delete_team(team_id: str) -> None:
    with transaction() as cur:
        cur.execute("DELETE FROM team WHERE id = %s", [path_uuid(team_id)])
        if cur.rowcount == 0:
            raise NotFoundError("Team not found.")


# --- memberships -------------------------------------------------------------

def list_members(team_id: str) -> List[dict]:
    tid = path_uuid(team_id)
    with transaction() as cur:
        _require_team(cur, tid)
        cur.execute(
            "SELECT p.id AS person_id, p.name, p.location, p.staff_type, "
            "m.role_in_team, m.joined_at "
            "FROM membership m JOIN person p ON p.id = m.person_id "
            "WHERE m.team_id = %s ORDER BY p.name",
            [tid],
        )
        return cur.fetchall()


def add_member(team_id: str, person_id, role_in_team: Optional[str]) -> dict:
    tid = path_uuid(team_id)
    with transaction() as cur:
        _require_team(cur, tid)
        _check_person(cur, person_id, "person_id")
        try:
            cur.execute(
                "INSERT INTO membership (team_id, person_id, role_in_team) "
                "VALUES (%s, %s, %s) "
                "RETURNING id, team_id, person_id, role_in_team, joined_at",
                [tid, person_id, role_in_team],
            )
        except psycopg.errors.UniqueViolation:
            raise ConflictError("That person is already a member of this team.")
        return cur.fetchone()


def update_member(team_id: str, person_id: str, role_in_team: Optional[str]) -> dict:
    with transaction() as cur:
        cur.execute(
            "UPDATE membership SET role_in_team = %s WHERE team_id = %s AND person_id = %s "
            "RETURNING id, team_id, person_id, role_in_team, joined_at",
            [role_in_team, path_uuid(team_id), path_uuid(person_id)],
        )
        row = cur.fetchone()
    if row is None:
        raise NotFoundError("Membership not found.")
    return row


def remove_member(team_id: str, person_id: str) -> None:
    with transaction() as cur:
        cur.execute(
            "DELETE FROM membership WHERE team_id = %s AND person_id = %s",
            [path_uuid(team_id), path_uuid(person_id)],
        )
        if cur.rowcount == 0:
            raise NotFoundError("Membership not found.")
