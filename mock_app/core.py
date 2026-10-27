"""
Lightweight, dependency-free mock application server.

Serves the static front-end under ``mock_app/static`` and a JSON REST API
registered with the ``@app.route`` decorator. It exists so the Playwright
suite can run end-to-end anywhere (laptop or GitHub Actions) without access
to a proprietary system under test.
"""
from __future__ import annotations

import json
import mimetypes
import re
import uuid
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse


class ApiError(Exception):
    """Raise inside a route to return a structured JSON error."""

    def __init__(self, status: int, message: str, field: str | None = None):
        super().__init__(message)
        self.status = status
        self.message = message
        self.field = field


@dataclass
class Request:
    method: str
    path: str
    params: dict
    query: dict
    body: dict
    headers: dict
    user: dict | None = None
    extra: dict = field(default_factory=dict)


class App:
    def __init__(self, static_dir: Path):
        self.static_dir = Path(static_dir).resolve()
        self.routes: list[tuple[str, re.Pattern, callable, bool]] = []
        self.tokens: dict[str, dict] = {}

    # ------------------------------------------------------------------ routing
    def route(self, method: str, pattern: str, auth: bool = True):
        compiled = re.compile("^" + pattern + "$")

        def decorator(fn):
            self.routes.append((method.upper(), compiled, fn, auth))
            return fn

        return decorator

    def issue_token(self, user: dict) -> str:
        token = uuid.uuid4().hex
        self.tokens[token] = user
        return token

    def revoke_all_tokens(self) -> None:
        self.tokens.clear()

    # ------------------------------------------------------------------ server
    def create_server(self, host: str = "127.0.0.1", port: int = 0) -> ThreadingHTTPServer:
        server = ThreadingHTTPServer((host, port), self._make_handler())
        server.daemon_threads = True
        return server

    def _make_handler(self):
        app = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):  # keep test output clean
                pass

            # ---- helpers
            def _send(self, status: int, body: bytes, content_type: str, extra_headers=None):
                self.send_response(status)
                self.send_header("Content-Type", content_type)
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Cache-Control", "no-store")
                for key, value in (extra_headers or {}).items():
                    self.send_header(key, value)
                self.end_headers()
                if self.command != "HEAD":
                    self.wfile.write(body)

            def _json(self, status: int, payload, extra_headers=None):
                self._send(status, json.dumps(payload).encode(), "application/json", extra_headers)

            def _read_body(self) -> dict:
                length = int(self.headers.get("Content-Length") or 0)
                if not length:
                    return {}
                raw = self.rfile.read(length)
                try:
                    data = json.loads(raw or b"{}")
                except json.JSONDecodeError as exc:
                    raise ApiError(400, "Malformed JSON body") from exc
                if not isinstance(data, dict):
                    raise ApiError(400, "JSON body must be an object")
                return data

            # ---- dispatch
            def _dispatch(self):
                parsed = urlparse(self.path)
                if parsed.path.startswith("/api/"):
                    return self._api(parsed)
                return self._static(parsed.path)

            def _api(self, parsed):
                try:
                    for method, pattern, fn, needs_auth in app.routes:
                        match = pattern.match(unquote(parsed.path))
                        if not match or method != self.command:
                            continue
                        user = None
                        if needs_auth:
                            auth = self.headers.get("Authorization", "")
                            token = auth.removeprefix("Bearer ").strip()
                            user = app.tokens.get(token)
                            if not user:
                                raise ApiError(401, "Authentication required")
                        req = Request(
                            method=self.command,
                            path=parsed.path,
                            params=match.groupdict(),
                            query={k: v[0] for k, v in parse_qs(parsed.query).items()},
                            body=self._read_body() if self.command in ("POST", "PUT", "PATCH") else {},
                            headers=dict(self.headers),
                            user=user,
                        )
                        result = fn(req)
                        if isinstance(result, tuple) and len(result) == 3:
                            status, payload, headers = result
                            if isinstance(payload, (bytes, str)):
                                body = payload.encode() if isinstance(payload, str) else payload
                                return self._send(status, body, headers.pop("Content-Type", "text/plain"), headers)
                            return self._json(status, payload, headers)
                        if isinstance(result, tuple):
                            return self._json(*result)
                        return self._json(200, result)
                    raise ApiError(404, f"No route for {self.command} {parsed.path}")
                except ApiError as err:
                    payload = {"error": err.message}
                    if err.field:
                        payload["field"] = err.field
                    return self._json(err.status, payload)
                except Exception as exc:  # pragma: no cover - surfaced to tests as 500
                    return self._json(500, {"error": f"Internal error: {exc}"})

            def _static(self, path: str):
                if path in ("", "/"):
                    return self._send(302, b"", "text/plain", {"Location": "/login.html"})
                target = (app.static_dir / path.lstrip("/")).resolve()
                if not target.is_relative_to(app.static_dir) or not target.is_file():
                    return self._send(404, b"Not found", "text/plain")
                ctype = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
                return self._send(200, target.read_bytes(), ctype)

            do_GET = do_POST = do_PUT = do_PATCH = do_DELETE = do_HEAD = _dispatch

        return Handler


def require(body: dict, name: str, label: str | None = None, strip: bool = True):
    """Return a required field or raise a 400 with the field name (passwords: strip=False)."""
    value = body.get(name)
    if value is None or (isinstance(value, str) and not value.strip()):
        raise ApiError(400, f"{label or name} is required", field=name)
    return value.strip() if isinstance(value, str) and strip else value
