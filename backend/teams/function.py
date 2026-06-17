"""teams service Lambda — CRUD plus a memberships sub-resource.

Routes (relative to the service):
  /                       GET list, POST create
  /{id}                   GET, PUT, DELETE
  /{id}/members           GET list, POST add (409 on duplicate)
  /{id}/members/{pid}     PUT update role, DELETE remove
All routes require authentication; mutations require the matching permission.
"""

import repository as repo
from models import MemberAdd, MemberUpdate, TeamCreate, TeamUpdate

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
    segments = resource_segments(request, "teams")
    method = request.method

    if not segments:
        if method == "GET":
            return _list(request)
        if method == "POST":
            require(claims, "create")
            return _create(request)
    elif len(segments) == 1:
        if method == "GET":
            return json_response(200, repo.get_team(segments[0]))
        if method == "PUT":
            require(claims, "update")
            return json_response(200, repo.update_team(segments[0], _team_body(request, TeamUpdate)))
        if method == "DELETE":
            require(claims, "delete")
            repo.delete_team(segments[0])
            return no_content()
    elif len(segments) == 2 and segments[1] == "members":
        if method == "GET":
            return json_response(200, {"data": repo.list_members(segments[0])})
        if method == "POST":
            require(claims, "create")
            return _add_member(request, segments[0])
    elif len(segments) == 3 and segments[1] == "members":
        if method == "PUT":
            require(claims, "update")
            model = validate(MemberUpdate, request.body)
            return json_response(200, repo.update_member(segments[0], segments[2], model.role_in_team))
        if method == "DELETE":
            require(claims, "delete")
            repo.remove_member(segments[0], segments[2])
            return no_content()

    raise NotFoundError("No matching route for this request.")


def _team_body(request: Request, model_cls) -> dict:
    return validate(model_cls, request.body).model_dump(mode="json")


def _list(request: Request) -> dict:
    query = request.query
    limit = as_int(query.get("limit"), _DEFAULT_PAGE, _MAX_PAGE)
    offset = as_int(query.get("offset"), 0)
    filters = {
        "location": query.get("location"),
        "reports_to_id": _opt_uuid_param(query.get("reports_to_id"), "reports_to_id"),
        "q": query.get("q"),
    }
    rows, total = repo.list_teams(filters, limit, offset)
    return collection(rows, limit, offset, total)


def _opt_uuid_param(value, field):
    """Validate an optional UUID query filter (400 on malformed input)."""
    if not value:
        return None
    try:
        return str(path_uuid(value))
    except NotFoundError:
        raise ValidationError(f"'{field}' must be a valid UUID.")


def _create(request: Request) -> dict:
    return json_response(201, repo.create_team(_team_body(request, TeamCreate)))


def _add_member(request: Request, team_id: str) -> dict:
    model = validate(MemberAdd, request.body)
    return json_response(201, repo.add_member(team_id, model.person_id, model.role_in_team))


handler = lambda_app(route)
