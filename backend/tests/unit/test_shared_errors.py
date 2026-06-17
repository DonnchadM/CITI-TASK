"""Unit tests: exception hierarchy and the error envelope."""

import json

from shared.errors import (
    AppError, ConflictError, Forbidden, NotFoundError, Unauthenticated, ValidationError,
)
from shared.http import error_response


def test_status_codes_and_codes():
    assert (AppError().status_code, AppError().code) == (500, "internal_error")
    assert (ValidationError().status_code, ValidationError().code) == (400, "validation_error")
    assert (NotFoundError().status_code, NotFoundError().code) == (404, "not_found")
    assert (ConflictError().status_code, ConflictError().code) == (409, "conflict")
    assert (Unauthenticated().status_code, Unauthenticated().code) == (401, "unauthenticated")
    assert (Forbidden().status_code, Forbidden().code) == (403, "forbidden")


def test_custom_message_and_details():
    err = ValidationError("bad input", details=[{"field": "name", "issue": "required"}])
    assert err.message == "bad input"
    assert err.details == [{"field": "name", "issue": "required"}]


def test_default_message_used_when_omitted():
    assert NotFoundError().message == NotFoundError.default_message
    assert NotFoundError().details == []


def test_error_response_envelope():
    response = error_response(NotFoundError("missing thing"))
    assert response["statusCode"] == 404
    body = json.loads(response["body"])
    assert body == {"error": {"code": "not_found", "message": "missing thing", "details": []}}
