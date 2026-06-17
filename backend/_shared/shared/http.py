"""HTTP helpers for Lambda Function URL events.

Covers request parsing (payload format 2.0), the uniform response envelopes from
the design, lightweight query-parameter coercion, Pydantic validation mapped to
the error envelope, and a decorator that turns a service ``route(request)``
function into a Lambda handler with consistent error handling and logging.
"""

import base64
import json
import logging
import uuid
from typing import Any, Callable, Dict, List, Optional, Type

from .errors import AppError, NotFoundError, ValidationError

logger = logging.getLogger()
if not logger.handlers:  # pragma: no cover - Lambda configures the root logger
    logging.basicConfig(level=logging.INFO)

_JSON_HEADERS = {"Content-Type": "application/json"}


class Request:
    """Parsed view of an incoming Function URL request."""

    def __init__(
        self,
        method: str,
        path: str,
        segments: List[str],
        query: Dict[str, str],
        body: Optional[dict],
        headers: Dict[str, str],
    ) -> None:
        self.method = method
        self.path = path
        self.segments = segments
        self.query = query
        self.body = body
        self.headers = headers


def parse_request(event: Optional[dict]) -> Request:
    """Build a :class:`Request` from a Function URL (v2) or API Gateway event."""
    event = event or {}
    http = (event.get("requestContext") or {}).get("http") or {}
    method = (http.get("method") or event.get("httpMethod") or "GET").upper()
    raw_path = event.get("rawPath") or http.get("path") or event.get("path") or "/"
    segments = [part for part in raw_path.split("/") if part]
    query = event.get("queryStringParameters") or {}
    headers = {k.lower(): v for k, v in (event.get("headers") or {}).items()}
    return Request(method, raw_path, segments, query, _parse_body(event), headers)


def _parse_body(event: dict) -> Optional[dict]:
    raw = event.get("body")
    if not raw:
        return None
    if event.get("isBase64Encoded"):
        raw = base64.b64decode(raw).decode("utf-8")
    try:
        return json.loads(raw)
    except (ValueError, TypeError):
        raise ValidationError("Request body is not valid JSON.")


def path_uuid(value: str) -> uuid.UUID:
    """Parse a path segment as a UUID; a malformed id matches no resource (404)."""
    try:
        return uuid.UUID(value)
    except (ValueError, AttributeError, TypeError):
        raise NotFoundError("The requested resource was not found.")


def resource_segments(request: Request, resource: str) -> List[str]:
    """Return path segments relative to the service.

    The local proxy strips the ``/api/<service>`` prefix, but CloudFront may
    forward it. Stripping a leading ``api`` and the resource name makes routing
    behave identically in both environments.
    """
    segments = list(request.segments)
    if segments and segments[0] == "api":
        segments = segments[1:]
    if segments and segments[0] == resource:
        segments = segments[1:]
    return segments


# --- Query-parameter coercion ------------------------------------------------

def as_int(value: Optional[str], default: int, maximum: Optional[int] = None) -> int:
    """Coerce a query value to a non-negative int, clamped to ``maximum``."""
    try:
        result = int(value) if value is not None else default
    except (ValueError, TypeError):
        raise ValidationError(f"Expected an integer, got '{value}'.")
    if result < 0:
        result = default
    if maximum is not None:
        result = min(result, maximum)
    return result


def as_bool(value: Optional[str]) -> Optional[bool]:
    """Coerce a query value to a bool; ``None`` when the parameter is absent."""
    if value is None:
        return None
    return value.lower() in ("1", "true", "yes")


# --- Validation --------------------------------------------------------------

def validate(model_cls: Type, data: Optional[dict]):
    """Validate ``data`` against a Pydantic model, mapping failures to HTTP 400."""
    from pydantic import ValidationError as PydanticValidationError

    if data is None:
        raise ValidationError("A request body is required.")
    try:
        return model_cls.model_validate(data)
    except PydanticValidationError as exc:
        details = [
            {
                "field": ".".join(str(p) for p in err["loc"]) or "(body)",
                "issue": err["msg"],
            }
            for err in exc.errors()
        ]
        raise ValidationError("Validation failed.", details=details)


# --- Response envelopes -------------------------------------------------------

def json_response(status: int, payload: Any) -> dict:
    """Serialise ``payload`` to a JSON Lambda response (UUID/datetime via str)."""
    return {
        "statusCode": status,
        "headers": _JSON_HEADERS,
        "body": json.dumps(payload, default=str),
    }


def no_content() -> dict:
    """HTTP 204 response with an empty body."""
    return {"statusCode": 204, "headers": _JSON_HEADERS, "body": ""}


def collection(items: List[dict], limit: int, offset: int, total: int) -> dict:
    """Wrap a list result in the standard paginated collection envelope."""
    return json_response(
        200,
        {"data": items, "pagination": {"limit": limit, "offset": offset, "total": total}},
    )


def error_response(error: AppError) -> dict:
    """Serialise an :class:`AppError` into the standard error envelope."""
    return json_response(
        error.status_code,
        {"error": {"code": error.code, "message": error.message, "details": error.details}},
    )


# --- Handler wrapper ----------------------------------------------------------

def lambda_app(route: Callable[[Request], dict]) -> Callable[..., dict]:
    """Wrap a ``route(request)`` function into a Lambda handler.

    Parses the event, attaches a correlation id to logs, and maps any
    :class:`AppError` to its envelope while logging (not leaking) unexpected
    errors as HTTP 500.
    """

    def handler(event: Optional[dict] = None, context: Any = None) -> dict:
        correlation_id = str(uuid.uuid4())
        try:
            request = parse_request(event)
            logger.info("[%s] %s %s", correlation_id, request.method, request.path)
            return route(request)
        except AppError as exc:
            logger.info("[%s] %s: %s", correlation_id, exc.code, exc.message)
            return error_response(exc)
        except Exception:
            logger.exception("[%s] Unhandled error", correlation_id)
            return error_response(AppError())

    return handler
