"""analytics service Lambda — read-only org metrics.

  /summary    GET org-wide KPI rollup (Q4-Q7 + total)
  /teams      GET per-team drill-down
Read-only: any authenticated role may read; there are no mutations.
"""

import repository as repo

from shared.auth import authenticate
from shared.db import ensure_schema
from shared.errors import NotFoundError
from shared.http import Request, json_response, lambda_app, resource_segments


def route(request: Request) -> dict:
    ensure_schema()
    authenticate(request)
    segments = resource_segments(request, "analytics")

    if request.method == "GET":
        if segments == ["summary"]:
            return json_response(200, repo.get_summary())
        if segments == ["teams"]:
            return json_response(200, {"data": repo.get_team_analytics()})

    raise NotFoundError("No matching route for this request.")


handler = lambda_app(route)
