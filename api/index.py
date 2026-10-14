"""Vercel serverless entrypoint.

Wraps the FastAPI app with Mangum so it runs as a Vercel Serverless
Function. Both `app` (native ASGI) and `handler` (Mangum) are exported;
Vercel picks up whichever its Python runtime prefers.

Notes for serverless:
- The Supabase backend is used when SUPABASE_URL / SUPABASE_KEY are set
  (set them in the Vercel dashboard). The local SQLite fallback is not
  usable on Vercel's read-only filesystem.
- The background scheduler only starts when ENABLE_SCHEDULER=1, which
  is never set on Vercel, so no background threads run here.
- Long scrapes may exceed the serverless function timeout; run heavy
  scrapers from the /scrapers page in small batches.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mangum import Mangum  # noqa: E402

from app.main import app  # noqa: E402

handler = Mangum(app, lifespan="off")
