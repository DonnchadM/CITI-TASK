"""Unit tests: Function-URL parsing, routing helpers, coercion, validation, envelopes."""

import base64
import json

import pytest
from pydantic import BaseModel, ConfigDict, Field

from shared.errors import NotFoundError, ValidationError
from shared.http import (
    as_bool, as_int, collection, json_response, no_content, parse_request,
    path_uuid, resource_segments, validate,
)


def event(method="GET", path="/", body=None, qs=None, b64=False):
    raw = None
    if body is not None:
        raw = base64.b64encode(body.encode()).decode() if b64 else body
    return {
        "rawPath": path,
        "requestContext": {"http": {"method": method}},
        "queryStringParameters": qs or {},
        "headers": {},
        "body": raw,
        "isBase64Encoded": b64,
    }


def test_parse_request_basics():
    req = parse_request(event("post", "/123", body='{"a": 1}', qs={"x": "y"}))
    assert req.method == "POST"
    assert req.segments == ["123"]
    assert req.query == {"x": "y"}
    assert req.body == {"a": 1}


def test_parse_request_base64_body():
    req = parse_request(event("POST", "/", body='{"hello": "world"}', b64=True))
    assert req.body == {"hello": "world"}


def test_parse_request_invalid_json_raises_400():
    with pytest.raises(ValidationError):
        parse_request(event("POST", "/", body="not json"))


def test_resource_segments_strips_api_and_resource_prefixes():
    # local proxy form
    assert resource_segments(parse_request(event("GET", "/")), "people") == []
    assert resource_segments(parse_request(event("GET", "/42")), "people") == ["42"]
    # cloud form where the /api/people prefix is forwarded
    assert resource_segments(parse_request(event("GET", "/api/people/42")), "people") == ["42"]


def test_path_uuid():
    valid = "5c138c12-bae5-4d49-b0a9-784d3053cd41"
    assert str(path_uuid(valid)) == valid
    with pytest.raises(NotFoundError):
        path_uuid("not-a-uuid")


def test_as_int_default_clamp_and_invalid():
    assert as_int(None, 50, 200) == 50
    assert as_int("999", 50, 200) == 200       # clamped to max
    assert as_int("-5", 50) == 50              # negative falls back to default
    with pytest.raises(ValidationError):
        as_int("abc", 50)


def test_as_bool():
    assert as_bool(None) is None
    assert as_bool("true") is True
    assert as_bool("1") is True
    assert as_bool("no") is False


class _Sample(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1)


def test_validate_success_and_failure():
    assert validate(_Sample, {"name": "ok"}).name == "ok"
    with pytest.raises(ValidationError) as exc:
        validate(_Sample, {"name": ""})
    assert exc.value.details and "field" in exc.value.details[0]
    with pytest.raises(ValidationError):
        validate(_Sample, None)  # missing body


def test_response_envelopes():
    assert no_content() == {"statusCode": 204, "headers": {"Content-Type": "application/json"}, "body": ""}
    single = json_response(201, {"id": 1})
    assert single["statusCode"] == 201 and json.loads(single["body"]) == {"id": 1}
    coll = collection([{"id": 1}], limit=50, offset=0, total=1)
    body = json.loads(coll["body"])
    assert body == {"data": [{"id": 1}], "pagination": {"limit": 50, "offset": 0, "total": 1}}
