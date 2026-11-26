"""Standard-library client for the 1VR Skill Store remote MCP server.

The store speaks the Model Context Protocol over streamable HTTP in stateless
mode: each call is a self-contained JSON-RPC 2.0 ``POST``, so there is no
``initialize`` handshake and no session id to carry between requests.

Health-check findings are factual records with sources, not a safety guarantee.
"""

from __future__ import annotations

import http.client
import time
import json
import os
import urllib.error
import urllib.request
from itertools import count
from typing import Any

__all__ = [
    "MCP_URL",
    "search_skills",
    "check_skill",
    "get_install_info",
]

MCP_URL = "https://1vr.com/mcp/skill-store"
USER_AGENT = "silicon-cafe-tools/0.1.0"
TIMEOUT = 30.0

_request_ids = count(1)


class _NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Refuse redirects so the bearer key is never replayed at another host.

    urllib follows 3xx responses transparently by default, which would resend
    the Authorization header to whatever location the server names. Returning
    None from redirect_request() stops that: the redirect surfaces to the
    caller as an error instead of being followed.
    """

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        """Return None: never build a follow-up request for this redirect."""
        return None


_OPENER = urllib.request.build_opener(_NoRedirectHandler())


def _rpc_call(tool_name, arguments, api_key=None, allow_retry=True):
    """Invoke a single MCP tool over JSON-RPC 2.0 on top of HTTP.

    Builds a ``tools/call`` request, posts it to ``MCP_URL`` with the
    module-level opener, and unwraps the ``result`` object from the
    response envelope. Redirects are refused by that opener, so a bearer
    key can never be forwarded to another host.

    A transport-level failure is retried once, after 0.5 seconds. Retries
    apply only to calls that record nothing on the server; authenticated
    ``get_install_info`` passes ``allow_retry=False`` because the server
    records the fetch, so a replay could record it twice.

    A key that is ``None``, empty, or whitespace-only counts as no key: such
    a call is anonymous and no ``Authorization`` header is attached.

    Args:
        tool_name: Name of the tool to call; sent as ``params.name``.
        arguments: Mapping of tool arguments; sent as ``params.arguments``.
        api_key: Optional bearer token. When given, an
            ``Authorization: Bearer <api_key>`` header is attached.
        allow_retry: When ``False``, exactly one attempt is made: the call
            is never retried and there is no sleep.

    Returns:
        dict: The ``result`` member of the JSON-RPC response envelope.

    Raises:
        RuntimeError: If the HTTP layer fails (non-2xx status, unreachable
            host, timeout), if the response body is not UTF-8 JSON or not a
            JSON object, if the envelope's ``jsonrpc`` member is neither
            absent nor ``"2.0"``, if its ``id`` does not match the id that
            was sent, if it carries a JSON-RPC ``error`` object, or if
            ``result`` is missing or is not a JSON object.
    """
    # An API key that is None, empty, or whitespace-only counts as no key.
    effective_key = api_key if (api_key is not None and str(api_key).strip()) else None

    request_id = next(_request_ids)
    payload = {
        "jsonrpc": "2.0",
        "id": request_id,
        "method": "tools/call",
        "params": {"name": tool_name, "arguments": arguments},
    }
    body = json.dumps(payload).encode("utf-8")

    raw = None
    transport_exc = None

    # At most two attempts: the first try plus one retry that is reserved
    # for transport-level failures only. When retrying is not allowed the
    # loop degenerates to a single attempt, with no sleep.
    attempts = (1, 2) if allow_retry else (1,)

    for attempt in attempts:
        request = urllib.request.Request(MCP_URL, data=body, method="POST")
        request.add_header("Content-Type", "application/json")
        request.add_header("Accept", "application/json")
        request.add_header("User-Agent", USER_AGENT)
        if effective_key is not None:
            request.add_header("Authorization", "Bearer {}".format(effective_key))

        transport_exc = None
        try:
            with _OPENER.open(request, timeout=TIMEOUT) as response:
                raw = response.read()
            break
        except TimeoutError as exc:
            transport_exc = exc
        except urllib.error.HTTPError as exc:
            # An HTTPError carries a status, so the server was reached and
            # answered: that is a protocol outcome, never retried.
            detail = ""
            try:
                detail = exc.read().decode("utf-8", "replace").strip()
            except Exception:
                detail = ""
            message = "MCP request failed with HTTP {} {}".format(exc.code, exc.reason)
            if detail:
                message += ": " + detail
            raise RuntimeError(message) from exc
        except (urllib.error.URLError, OSError, http.client.HTTPException) as exc:
            # HTTPError is a URLError subclass too, but it was handled above,
            # so everything caught here is a pure transport failure.
            transport_exc = exc

        if allow_retry and attempt == 1:
            time.sleep(0.5)

    if transport_exc is not None:
        if isinstance(transport_exc, TimeoutError):
            raise RuntimeError(
                "MCP request to {} timed out after {} seconds".format(MCP_URL, TIMEOUT)
            ) from transport_exc
        if isinstance(transport_exc, urllib.error.URLError):
            raise RuntimeError(
                "Could not reach MCP server at {}: {}".format(
                    MCP_URL, transport_exc.reason
                )
            ) from transport_exc
        raise RuntimeError(
            "Transport error talking to MCP server at {}: {}".format(MCP_URL, transport_exc)
        ) from transport_exc

    try:
        text = raw.decode("utf-8")
    except Exception as exc:
        raise RuntimeError("MCP response body was not valid UTF-8") from exc

    try:
        envelope = json.loads(text)
    except ValueError as exc:
        raise RuntimeError("MCP response body was not valid JSON") from exc

    if not isinstance(envelope, dict):
        raise RuntimeError(
            "MCP response envelope was {}, expected a JSON object".format(
                type(envelope).__name__
            )
        )

    # A missing version field is tolerated for compatibility; an explicit
    # null or any other value is not.
    if "jsonrpc" in envelope and envelope["jsonrpc"] != "2.0":
        raise RuntimeError(
            "MCP response declared unsupported jsonrpc version {!r}".format(
                envelope["jsonrpc"]
            )
        )

    # Reject bool ids explicitly: in Python, True == 1 would otherwise pass.
    if isinstance(envelope.get("id"), bool) or envelope.get("id") != request_id:
        raise RuntimeError(
            "MCP response id {!r} did not match request id {!r}".format(
                envelope.get("id"), request_id
            )
        )

    error = envelope.get("error")
    if error is not None:
        if isinstance(error, dict):
            detail = error.get("message")
            if not detail:
                detail = json.dumps(error)
            code = error.get("code")
            if code is not None:
                raise RuntimeError("MCP error {}: {}".format(code, detail))
            raise RuntimeError("MCP error: {}".format(detail))
        raise RuntimeError("MCP error: {}".format(error))

    result = envelope.get("result")
    if not isinstance(result, dict):
        raise RuntimeError(
            "MCP response 'result' was {}, expected a JSON object".format(
                type(result).__name__
            )
        )

    return result


def _unwrap(result: Any) -> Any:
    """Flatten an MCP tool result into a plain Python value.

    If result["isError"] is True, raise RuntimeError carrying the
    concatenated text of every text content item (or "tool returned an
    error" when no such text is present).

    Otherwise prefer result["structuredContent"] when it is not None.
    Failing that, take the first content item of type "text", run
    json.loads on its text and return the parsed value, falling back to
    {"text": text} when parsing fails. When there are no content items at
    all, return result unchanged.
    """
    if result.get("isError") is True:
        content = result.get("content") or []
        text = "".join(
            item.get("text", "")
            for item in content
            if item.get("type") == "text"
        )
        raise RuntimeError(
            "Skill Store MCP tool error: " + (text or "tool returned an error")
        )

    structured = result.get("structuredContent")
    if structured is not None:
        return structured

    content = result.get("content") or []
    if not content:
        return result

    for item in content:
        if item.get("type") == "text":
            text = item.get("text", "")
            try:
                return json.loads(text)
            except (TypeError, ValueError):
                return {"text": text}

    return result


def search_skills(
    q: str,
    category: str | None = None,
    lang: str | None = None,
    limit: int = 8,
) -> Any:
    """Search the 3,175 agent skills in the 1VR Skill Store by task or keyword.

    Each hit carries install information plus a summary of the health-check
    (audit) signals recorded for that skill.

    Args:
        q: Free-text task or keyword query.
        category: Optional category filter.
        lang: Optional language filter.
        limit: Maximum number of results, 1-20 (default 8).

    Returns:
        The tool payload: either the parsed JSON value or ``{"text": ...}``.

    Note:
        Health-check findings are factual records with sources, not a safety
        guarantee.
    """
    arguments: dict[str, Any] = {"q": q}
    if category is not None:
        arguments["category"] = category
    if lang is not None:
        arguments["lang"] = lang
    arguments["limit"] = limit
    return _unwrap(_rpc_call("search_skills", arguments))


def check_skill(skill_id: int) -> Any:
    """Fetch the pre-install audit signals recorded for one skill.

    Returns the factual health-check record — tier, ``checked_at``, and findings
    grouped by category with their sources. It certifies nothing.

    Args:
        skill_id: Numeric skill identifier from a search result.

    Returns:
        The tool payload: either the parsed JSON value or ``{"text": ...}``.

    Note:
        Health-check findings are factual records with sources, not a safety
        guarantee.
    """
    return _unwrap(_rpc_call("check_skill", {"skill_id": skill_id}))


def get_install_info(skill_id: int, api_key: str | None = None) -> Any:
    """Get ready-to-run install text and the source link for one skill.

    When an API key is available the request is authenticated with it, so the
    fetch is recorded in the store's install log under the caller's own
    identity. Without a key the store returns public install info only. No
    automatic retry is performed when a key is sent, because the server
    records the fetch and a replay could record it twice.

    The ``api_key`` argument is resolved in three distinct cases:

    * ``None`` — no key was supplied, so ``TEA_API_KEY`` is read from the
      environment as a fallback.
    * A non-empty string — used as the key exactly as given; the environment
      is never consulted.
    * An empty or whitespace-only string — the caller is explicitly asking for
      an anonymous call, so the environment is deliberately *not* consulted.

    Whatever the source, an empty or whitespace-only effective key is
    normalized to ``None``: the call is anonymous, carries no
    ``Authorization`` header, and is retried like any other unauthenticated
    call.

    Args:
        skill_id: Numeric skill identifier from a search result.
        api_key: Optional 1VR agent API key. ``None`` falls back to
            ``TEA_API_KEY`` in the environment; a non-empty string is used
            as-is; an empty or whitespace-only string forces anonymity.

    Returns:
        The tool payload: either the parsed JSON value or ``{"text": ...}``.
    """
    # Resolve the three cases: only an omitted key (None) may fall back to the
    # environment; an explicit empty string means "anonymous, ignore the env".
    key = os.environ.get("TEA_API_KEY") if api_key is None else api_key
    # An empty or whitespace-only key is no key at all.
    if key is not None and not str(key).strip():
        key = None
    return _unwrap(
        _rpc_call(
            "get_install_info",
            {"skill_id": skill_id},
            api_key=key,
            allow_retry=not key,
        )
    )
