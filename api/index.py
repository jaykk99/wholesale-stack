"""Vercel serverless entrypoint.

Exports the FastAPI app directly as an ASGI app — Vercel's Python runtime
serves it natively. The vercel.json rewrite sends every path here with the
original path in the __path query param; the wrapper restores it so the
FastAPI routes match.
"""

from urllib.parse import parse_qs

from app.main import app as fastapi_app


async def app(scope, receive, send):
    if scope["type"] == "http":
        path = scope.get("path", "")
        qs = parse_qs(scope.get("query_string", b"").decode())
        orig = (qs.get("__path") or [None])[0]
        if orig:
            # Rewritten request: restore the original path, drop __path param
            pairs = parse_qs(scope.get("query_string", b"").decode(), keep_blank_values=True)
            pairs.pop("__path", None)
            new_qs = "&".join(f"{k}={v}" for k, vs in pairs.items() for v in vs)
            scope = {**scope, "path": orig, "raw_path": orig.encode(),
                     "query_string": new_qs.encode()}
        elif path == "/api/index":
            scope = {**scope, "path": "/", "raw_path": b"/"}
        elif path.startswith("/api/index/"):
            new_path = path[len("/api/index"):]
            scope = {**scope, "path": new_path, "raw_path": new_path.encode()}
    await fastapi_app(scope, receive, send)
