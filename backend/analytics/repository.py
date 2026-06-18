"""Read-only analytics over the team_analytics view.

The view (defined in shared/schema.sql) is the single source of truth for the
per-team metrics; the summary is just a rollup of it, so KPIs and drill-down stay
consistent by construction.
"""

from typing import List

from shared.db import transaction

# Achievement counts are joined in here rather than added to the team_analytics
# view: the view already LEFT JOINs membership, so an achievement join would fan
# out and inflate member_count/non_direct_count. A pre-aggregated subquery keeps
# the structural metrics intact while still surfacing achievement activity.
_SUMMARY_SQL = """
    SELECT
      COUNT(*)                                        AS total_teams,
      COUNT(*) FILTER (WHERE leader_not_colocated)    AS teams_leader_not_colocated,
      COUNT(*) FILTER (WHERE leader_is_non_direct)    AS teams_leader_non_direct,
      COUNT(*) FILTER (WHERE non_direct_ratio > 0.20) AS teams_high_non_direct_ratio,
      COUNT(*) FILTER (WHERE reports_to_org_leader)   AS teams_under_org_leader,
      (SELECT COUNT(*) FROM achievement)              AS total_achievements,
      (SELECT COUNT(*) FROM achievement
         WHERE month = date_trunc('month', CURRENT_DATE)::date) AS achievements_this_month
    FROM team_analytics
"""

_TEAMS_SQL = """
    SELECT ta.team_id, ta.team_name, ta.team_location, ta.leader_id, ta.leader_location,
           ta.leader_staff_type, ta.leader_not_colocated, ta.leader_is_non_direct,
           ta.member_count, ta.non_direct_count, ta.non_direct_ratio, ta.reports_to_org_leader,
           COALESCE(ac.cnt, 0) AS achievement_count
    FROM team_analytics ta
    LEFT JOIN (
        SELECT team_id, COUNT(*) AS cnt FROM achievement GROUP BY team_id
    ) ac ON ac.team_id = ta.team_id
    ORDER BY ta.team_name
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
