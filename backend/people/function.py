"""people service Lambda — CRUD for Person plus a teams sub-resource.

Routing is derived from the Function URL path (resolved relative to the service
so it works whether or not the ``/api/people`` prefix is forwarded). Validation,
DB access, and error handling come from the shared module; this file only maps
routes to repository calls.
"""

import repository as repo
from models import PersonCreate, PersonUpdate
from shared.auth import authenticate, require
from shared.db import ensure_schema
from shared.errors import NotFoundError
from shared.http import (
    Request,
    as_bool,
    as_int,
    collection,
    json_response,
    lambda_app,
    no_content,
    resource_segments,
    validate,
)

_MAX_PAGE = 200
_DEFAULT_PAGE = 50


def route(request: Request) -> dict:
    """Dispatch a request to the matching handler.

    All routes require authentication; mutations additionally require the
    matching permission (create/update/delete) via the shared RBAC matrix.
    """
    ensure_schema()
    claims = authenticate(request)
    segments = resource_segments(request, "people")
    method = request.method

    if not segments:
        if method == "GET":
            return _list(request)
        if method == "POST":
            require(claims, "create")
            return _create(request)
    elif len(segments) == 1:
        if method == "GET":
            return json_response(200, repo.get_person(segments[0]))
        if method == "PUT":
            require(claims, "update")
            return _update(segments[0], request)
        if method == "DELETE":
            require(claims, "delete")
            repo.delete_person(segments[0])
            return no_content()
    elif len(segments) == 2 and segments[1] == "teams" and method == "GET":
        return json_response(200, {"data": repo.list_person_teams(segments[0])})

    raise NotFoundError("No matching route for this request.")


def _list(request: Request) -> dict:
    query = request.query
    limit = as_int(query.get("limit"), _DEFAULT_PAGE, _MAX_PAGE)
    offset = as_int(query.get("offset"), 0)
    filters = {
        "location": query.get("location"),
        "staff_type": query.get("staff_type"),
        "is_org_leader": as_bool(query.get("is_org_leader")),
        "q": query.get("q"),
    }
    rows, total = repo.list_people(filters, limit, offset)
    return collection(rows, limit, offset, total)


def _create(request: Request) -> dict:
    model = validate(PersonCreate, request.body)
    return json_response(201, repo.create_person(model.model_dump(mode="json")))


def _update(person_id: str, request: Request) -> dict:
    model = validate(PersonUpdate, request.body)
    return json_response(200, repo.update_person(person_id, model.model_dump(mode="json")))


handler = lambda_app(route)
