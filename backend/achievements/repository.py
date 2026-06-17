"""SQL data access for team achievements."""

from datetime import date
from typing import List, Optional, Tuple

from shared.db import transaction
from shared.errors import NotFoundError, ValidationError
from shared.http import path_uuid

_COLUMNS = "id, team_id, month, title, description, created_at, updated_at"


def _check_team(cur, team_id) -> None:
    cur.execute("SELECT 1 FROM team WHERE id = %s", [team_id])
    if cur.fetchone() is None:
        raise ValidationError(
            "A referenced team does not exist.",
            details=[{"field": "team_id", "issue": "no team with that id"}],
        )


def list_achievements(filters: dict, limit: int, offset: int) -> Tuple[List[dict], int]:
    where: List[str] = []
    params: List[object] = []
    if filters.get("team_id"):
        where.append("team_id = %s")
        params.append(filters["team_id"])
    if filters.get("month"):
        where.append("month = %s")
        params.append(filters["month"])
    if filters.get("from"):
        where.append("month >= %s")
        params.append(filters["from"])
    if filters.get("to"):
        where.append("month <= %s")
        params.append(filters["to"])

    clause = f"WHERE {' AND '.join(where)}" if where else ""
    with transaction() as cur:
        cur.execute(f"SELECT COUNT(*) AS total FROM achievement {clause}", params)  # nosec B608 - parameterized query; only code-controlled identifiers are interpolated
        total = cur.fetchone()["total"]
        cur.execute(
            f"SELECT {_COLUMNS} FROM achievement {clause} "  # nosec B608 - parameterized query; only code-controlled identifiers are interpolated
            f"ORDER BY month DESC, created_at DESC LIMIT %s OFFSET %s",
            [*params, limit, offset],
        )
        return cur.fetchall(), total


def get_achievement(achievement_id: str) -> dict:
    with transaction() as cur:
        cur.execute(
            f"SELECT {_COLUMNS} FROM achievement WHERE id = %s", [path_uuid(achievement_id)]  # nosec B608 - parameterized query; only code-controlled identifiers are interpolated
        )
        row = cur.fetchone()
    if row is None:
        raise NotFoundError("Achievement not found.")
    return row


def create_achievement(data: dict) -> dict:
    with transaction() as cur:
        _check_team(cur, data["team_id"])
        cur.execute(
            f"INSERT INTO achievement (team_id, month, title, description) "  # nosec B608 - parameterized query; only code-controlled identifiers are interpolated
            f"VALUES (%s, %s, %s, %s) RETURNING {_COLUMNS}",
            [data["team_id"], data["month"], data["title"], data["description"]],
        )
        return cur.fetchone()


def update_achievement(achievement_id: str, data: dict) -> dict:
    with transaction() as cur:
        _check_team(cur, data["team_id"])
        cur.execute(
            f"UPDATE achievement SET team_id = %s, month = %s, title = %s, description = %s, "  # nosec B608 - parameterized query; only code-controlled identifiers are interpolated
            f"updated_at = now() WHERE id = %s RETURNING {_COLUMNS}",
            [data["team_id"], data["month"], data["title"], data["description"],
             path_uuid(achievement_id)],
        )
        row = cur.fetchone()
    if row is None:
        raise NotFoundError("Achievement not found.")
    return row


def delete_achievement(achievement_id: str) -> None:
    with transaction() as cur:
        cur.execute("DELETE FROM achievement WHERE id = %s", [path_uuid(achievement_id)])
        if cur.rowcount == 0:
            raise NotFoundError("Achievement not found.")
