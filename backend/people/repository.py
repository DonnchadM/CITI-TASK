"""SQL data access for the person resource.

All queries are parameterized and run inside :func:`shared.db.transaction`, so a
failure rolls the request back. Returned rows are plain dicts (dict_row factory);
``shared.http.json_response`` serialises UUID/datetime/JSONB values.
"""

from typing import List, Optional, Tuple

from psycopg.types.json import Json

from shared.db import transaction
from shared.errors import NotFoundError
from shared.http import path_uuid

# Columns returned by every person query, in a stable order.
_COLUMNS = (
    "id, name, location, staff_type, title, is_org_leader, "
    "metadata, created_at, updated_at"
)


def list_people(
    filters: dict, limit: int, offset: int
) -> Tuple[List[dict], int]:
    """Return a page of people matching the filters plus the total match count."""
    where: List[str] = []
    params: List[object] = []
    if filters.get("location"):
        where.append("location = %s")
        params.append(filters["location"])
    if filters.get("staff_type"):
        where.append("staff_type = %s")
        params.append(filters["staff_type"])
    if filters.get("is_org_leader") is not None:
        where.append("is_org_leader = %s")
        params.append(filters["is_org_leader"])
    if filters.get("q"):
        where.append("(name ILIKE %s OR title ILIKE %s)")
        params.extend([f"%{filters['q']}%", f"%{filters['q']}%"])

    clause = f"WHERE {' AND '.join(where)}" if where else ""
    with transaction() as cur:
        cur.execute(f"SELECT COUNT(*) AS total FROM person {clause}", params)  # nosec B608 - parameterized query; only code-controlled identifiers are interpolated
        total = cur.fetchone()["total"]
        cur.execute(
            f"SELECT {_COLUMNS} FROM person {clause} "  # nosec B608 - parameterized query; only code-controlled identifiers are interpolated
            f"ORDER BY created_at DESC, id LIMIT %s OFFSET %s",
            [*params, limit, offset],
        )
        return cur.fetchall(), total


def get_person(person_id: str) -> dict:
    """Return one person or raise :class:`NotFoundError`."""
    pid = path_uuid(person_id)
    with transaction() as cur:
        cur.execute(f"SELECT {_COLUMNS} FROM person WHERE id = %s", [pid])  # nosec B608 - parameterized query; only code-controlled identifiers are interpolated
        row = cur.fetchone()
    if row is None:
        raise NotFoundError("Person not found.")
    return row


def create_person(data: dict) -> dict:
    """Insert a person and return the created row."""
    with transaction() as cur:
        cur.execute(
            f"INSERT INTO person (name, location, staff_type, title, is_org_leader, metadata) "  # nosec B608 - parameterized query; only code-controlled identifiers are interpolated
            f"VALUES (%s, %s, %s, %s, %s, %s) RETURNING {_COLUMNS}",
            [
                data["name"],
                data["location"],
                data["staff_type"],
                data["title"],
                data["is_org_leader"],
                Json(data["metadata"]),
            ],
        )
        return cur.fetchone()


def update_person(person_id: str, data: dict) -> dict:
    """Full-update a person; raise :class:`NotFoundError` if it does not exist."""
    pid = path_uuid(person_id)
    with transaction() as cur:
        cur.execute(
            f"UPDATE person SET name = %s, location = %s, staff_type = %s, title = %s, "  # nosec B608 - parameterized query; only code-controlled identifiers are interpolated
            f"is_org_leader = %s, metadata = %s, updated_at = now() "
            f"WHERE id = %s RETURNING {_COLUMNS}",
            [
                data["name"],
                data["location"],
                data["staff_type"],
                data["title"],
                data["is_org_leader"],
                Json(data["metadata"]),
                pid,
            ],
        )
        row = cur.fetchone()
    if row is None:
        raise NotFoundError("Person not found.")
    return row


def delete_person(person_id: str) -> None:
    """Delete a person; raise :class:`NotFoundError` if it does not exist."""
    pid = path_uuid(person_id)
    with transaction() as cur:
        cur.execute("DELETE FROM person WHERE id = %s", [pid])
        if cur.rowcount == 0:
            raise NotFoundError("Person not found.")


def list_person_teams(person_id: str) -> List[dict]:
    """Return the teams a person belongs to (via membership)."""
    get_person(person_id)  # 404 if the person does not exist
    with transaction() as cur:
        cur.execute(
            "SELECT t.id, t.name, t.location, m.role_in_team, m.joined_at "
            "FROM membership m JOIN team t ON t.id = m.team_id "
            "WHERE m.person_id = %s ORDER BY m.joined_at",
            [path_uuid(person_id)],
        )
        return cur.fetchall()
