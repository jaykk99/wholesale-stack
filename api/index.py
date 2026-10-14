"""Vercel serverless entrypoint.

Exports the FastAPI app directly as an ASGI app — Vercel's Python runtime
serves it natively. The vercel.json rewrite sends every path here; the
wrapper strips the /api/index prefix so routes see the original path.
"""

from app.main import app as fastapi_app


async def app(scope, receive, send):
    if scope["type"] == "http":
        path = scope.get("path", "")
        if path == "/api/index":
            scope = {**scope, "path": "/", "raw_path": b"/"}
        elif path.startswith("/api/index/"):
            new_path = path[len("/api/index"):]
            scope = {**scope, "path": new_path, "raw_path": new_path.encode()}
    await fastapi_app(scope, receive, send)
