"""Report unhandled exceptions to Error Inbox (POST /api/v1/errors).

Off unless ERROR_INBOX_URL and ERROR_INBOX_KEY (an eibx_ owner key) are set.
Fire-and-forget on a daemon thread, de-duped per signature and capped per hour,
so reporting can never slow or break a request.
"""
import hashlib
import logging
import os
import threading
import time
import traceback

import httpx

log = logging.getLogger("wholesale.error_report")

REPO = os.environ.get("ERROR_INBOX_REPO", "jaykk99/wholesale-stack")
DEDUPE_SECONDS = 3600
MAX_PER_HOUR = 20
_seen: dict[str, float] = {}
_sent: list[float] = []
_lock = threading.Lock()


def enabled() -> bool:
    return bool(os.environ.get("ERROR_INBOX_URL") and os.environ.get("ERROR_INBOX_KEY"))


def _signature(exc: BaseException, path: str) -> str:
    tb = traceback.extract_tb(exc.__traceback__)
    where = f"{tb[-1].filename}:{tb[-1].lineno}" if tb else ""
    return hashlib.sha1(f"{type(exc).__name__}|{where}|{path}".encode()).hexdigest()


def _should_send(sig: str, now: float) -> bool:
    with _lock:
        _sent[:] = [t for t in _sent if now - t < 3600]
        if len(_sent) >= MAX_PER_HOUR or now - _seen.get(sig, 0) < DEDUPE_SECONDS:
            return False
        _seen[sig] = now
        _sent.append(now)
        return True


def _post(text: str) -> None:
    url = os.environ["ERROR_INBOX_URL"].rstrip("/") + "/api/v1/errors"
    try:
        r = httpx.post(url, json={"target_kind": "repo", "target_value": REPO, "error_text": text},
                       headers={"Authorization": f"Bearer {os.environ['ERROR_INBOX_KEY']}"}, timeout=30)
        if r.status_code >= 400:
            log.warning("Error Inbox rejected report: %s %s", r.status_code, r.text[:200])
    except Exception:
        log.warning("could not reach Error Inbox", exc_info=True)


def report(exc: BaseException, method: str = "", path: str = "") -> bool:
    """Queue a report. Returns True if one was dispatched."""
    if not enabled() or not _should_send(_signature(exc, path), time.time()):
        return False
    tb = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))[-4000:]
    text = f"Unhandled {type(exc).__name__} in wholesale-stack on {method} {path}\n\n{tb}"
    threading.Thread(target=_post, args=(text,), daemon=True).start()
    return True
