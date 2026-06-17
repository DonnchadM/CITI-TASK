"""achievements service Lambda — CRUD with team/month/date-range filters.

  /         GET list (?team_id=&month=&from=&to=), POST create
  /{id}     GET, PUT, DELETE
All routes require authentication; mutations require the matching permission.
"""

from datetime import date

import repository as repo
from models import AchievementCreate, AchievementUpdate

from shared.auth import authenticate, require
from shared.db import ensure_schema
from shared.errors import NotFoundError, ValidationError
from shared.http import (
    Request,
    as_int,
    collection,
    json_response,
    lambda_app,
    no_content,
    path_uuid,
    resource_segments,
    validate,
)

_MAX_PAGE = 200
_DEFAULT_PAGE = 50


def route(request: Request) -> dict:
    ensure_schema()
    claims = authenticate(request)
    segments = resource_segments(request, "achievements")
    method = request.method

    if not segments:
        if method == "GET":
            return _list(request)
        if method == "POST":
            require(claims, "create")
            return json_response(201, repo.create_achievement(_body(request, AchievementCreate)))
    elif len(segments) == 1:
        if method == "GET":
            return json_response(200, repo.get_achievement(segments[0]))
        if method == "PUT":
            require(claims, "update")
            return json_response(200, repo.update_achievement(segments[0], _body(request, AchievementUpdate)))
        if method == "DELETE":
            require(claims, "delete")
            repo.delete_achievement(segments[0])
            return no_content()

    raise NotFoundError("No matching route for this request.")


def _body(request: Request, model_cls) -> dict:
    return validate(model_cls, request.body).model_dump(mode="json")


def _list(request: Request) -> dict:
    query = request.query
    limit = as_int(query.get("limit"), _DEFAULT_PAGE, _MAX_PAGE)
    offset = as_int(query.get("offset"), 0)
    filters = {
        "team_id": _opt_uuid_param(query.get("team_id")),
        "month": _date_param(query.get("month"), "month", first_of_month=True),
        "from": _date_param(query.get("from"), "from"),
        "to": _date_param(query.get("to"), "to"),
    }
    rows, total = repo.list_achievements(filters, limit, offset)
    return collection(rows, limit, offset, total)


def _opt_uuid_param(value):
    if not value:
        return None
    try:
        return str(path_uuid(value))
    except NotFoundError:
        raise ValidationError("'team_id' must be a valid UUID.")


def _date_param(value, field: str, first_of_month: bool = False):
    """Validate an optional ISO date query filter (400 on malformed input)."""
    if not value:
        return None
    try:
        parsed = date.fromisoformat(value)
    except ValueError:
        raise ValidationError(f"'{field}' must be an ISO date (YYYY-MM-DD).")
    return parsed.replace(day=1) if first_of_month else parsed


handler = lambda_app(route)
