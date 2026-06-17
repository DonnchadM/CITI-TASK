"""assistant service Lambda — natural-language "Ask the org" over our own data.

Claude (claude-opus-4-8) interprets the question and calls read-only tools that
mirror our analytics/list endpoints (tools.py); we execute them against the
locked data surface and Claude composes a grounded answer. No text-to-SQL, no
writes — the model can only see what the tools expose. The Anthropic key is read
from the environment server-side and never leaves the backend.

  POST /assistant/query  { "question": "..." }  ->  { "answer": "...", "data": [...] }
"""

import os

import anthropic
import models
import tools

from shared.auth import authenticate
from shared.db import ensure_schema
from shared.errors import AppError, NotFoundError
from shared.http import Request, json_response, lambda_app, resource_segments, validate

MODEL = "claude-opus-4-8"
MAX_ROUNDS = 6
MAX_TOKENS = 4096

SYSTEM_PROMPT = (
    "You are the analytics assistant for a Team Management application. Answer questions "
    "about teams, people, locations, monthly achievements, and the organizational KPIs "
    "(leader co-location, non-direct staff ratios, reporting hierarchy) using ONLY the "
    "provided tools. Call tools to gather data; never invent names, numbers, or facts. If "
    "the tools do not contain the answer, say so plainly. Be concise and direct."
)


class AssistantUnavailable(AppError):
    """The assistant is not configured (no API key) or upstream auth failed (HTTP 503)."""

    status_code = 503
    code = "assistant_unavailable"
    default_message = "The AI assistant is not configured. Set ANTHROPIC_API_KEY."


def route(request: Request) -> dict:
    ensure_schema()
    authenticate(request)  # any authenticated user may ask (read-only)
    segments = resource_segments(request, "assistant")
    if segments == ["query"] and request.method == "POST":
        data = validate(models.AssistantQuery, request.body)
        answer, used = _ask(data.question)
        return json_response(200, {"answer": answer, "data": used})
    raise NotFoundError("No matching route for this request.")


def _ask(question: str):
    if not os.getenv("ANTHROPIC_API_KEY"):
        raise AssistantUnavailable()
    client = anthropic.Anthropic()

    messages = [{"role": "user", "content": question}]
    used = []
    response = None
    try:
        for _ in range(MAX_ROUNDS):
            response = client.messages.create(
                model=MODEL,
                max_tokens=MAX_TOKENS,
                system=SYSTEM_PROMPT,
                tools=tools.TOOLS,
                messages=messages,
                thinking={"type": "adaptive"},
                output_config={"effort": "low"},  # keep latency under the CDN timeout
            )
            if response.stop_reason != "tool_use":
                break
            messages.append({"role": "assistant", "content": response.content})
            results = []
            for block in response.content:
                if block.type == "tool_use":
                    used.append({"tool": block.name, "input": block.input})
                    results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": tools.run_tool(block.name, block.input),
                    })
            messages.append({"role": "user", "content": results})
    except anthropic.AuthenticationError:
        raise AssistantUnavailable("The AI assistant's API key is invalid.")
    except anthropic.APIError as exc:
        raise AppError(f"The AI assistant is temporarily unavailable: {exc}")

    answer = "".join(b.text for b in (response.content if response else []) if b.type == "text")
    return (answer or "I couldn't determine an answer from the available data."), used


handler = lambda_app(route)
