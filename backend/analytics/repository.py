"""Read-only analytics over the team_analytics view.

The view (defined in shared/schema.sql) is the single source of truth for the
per-team metrics; the summary is just a rollup of it, so KPIs and drill-down stay
consistent by construction.
"""

from typing import List

from shared.db import transaction

_SUMMARY_SQL = """
    SELECT
      COUNT(*)                                        AS total_teams,
      COUNT(*) FILTER (WHERE leader_not_colocated)    AS teams_leader_not_colocated,
      COUNT(*) FILTER (WHERE leader_is_non_direct)    AS teams_leader_non_direct,
      COUNT(*) FILTER (WHERE non_direct_ratio > 0.20) AS teams_high_non_direct_ratio,
      COUNT(*) FILTER (WHERE reports_to_org_leader)   AS teams_under_org_leader
    FROM team_analytics
"""

_TEAMS_SQL = """
    SELECT team_id, team_name, team_location, leader_id, leader_location,
           leader_staff_type, leader_not_colocated, leader_is_non_direct,
           member_count, non_direct_count, non_direct_ratio, reports_to_org_leader
    FROM team_analytics
    ORDER BY team_name
"""


def get_summary() -> dict:
    """Return the org-wide KPI rollup (Q4-Q7 plus the team total)."""
    with transaction() as cur:
        cur.execute(_SUMMARY_SQL)
        return cur.fetchone()


def get_team_analytics() -> List[dict]:
    """Return per-team metrics for drill-down; ratio as a float for clean JSON."""
    with transaction() as cur:
        cur.execute(_TEAMS_SQL)
        rows = cur.fetchall()
    for row in rows:
        if row.get("non_direct_ratio") is not None:
            row["non_direct_ratio"] = float(row["non_direct_ratio"])
    return rows
