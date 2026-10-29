"""Crypto checkout for Wholesale Stack, powered by the vendored paywatch package.

What "paid" means in this app: when the watcher unlocks an order, the
on_unlock callback below records a durable entitlement row in a local
SQLite table (`crypto_entitlements`, in the paywatch database file) and,
when the buyer_ref points at a lead (`lead:<id>`), adds a note to that
lead in the CRM. Wholesale Stack is an internal CRM with no public
accounts or subscriptions, so the entitlement row plus the lead note is
the paid flag: it is what staff check before treating a buyer or lead as
paid up. The Cloudflare Worker version in `cloudflare-checkout/` keeps
the same entitlement idea in D1.

Plans come from, in order: PAYWATCH_PLANS_JSON, WHOLESALE_PLANS_JSON,
then the repo file `paywatch_plans.json`. That file ships PLACEHOLDER
tiers only, because Wholesale Stack has no real crypto pricing yet.
While any plan id starts with `placeholder_`, the checkout page hides
prices and shows a pricing-not-set warning instead of inventing prices.

Receive addresses come from the paywatch package: environment pools win
per asset, otherwise the shipped default pools in
`paywatch/default_addresses.json` apply (the owner's public receive
addresses for BTC, ETH, BNB, and SOL).
"""
from __future__ import annotations

import json
import os
import sqlite3
import threading
import time
from typing import Optional

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

_watcher = None
_watcher_lock = threading.Lock()
_test_watcher = None


def plans_source():
    """Raw plans payload from env or the repo plans file."""
    raw = os.environ.get("PAYWATCH_PLANS_JSON") or os.environ.get("WHOLESALE_PLANS_JSON")
    if raw:
        return raw
    path = os.environ.get("PAYWATCH_PLANS_FILE") or os.path.join(BASE_DIR, "paywatch_plans.json")
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def plans_are_placeholder(plans: dict) -> bool:
    return any(str(pid).startswith("placeholder") for pid in plans)


def db_path() -> str:
    return (os.environ.get("WHOLESALE_CRYPTO_DB")
            or os.environ.get("PAYWATCH_DB_PATH")
            or os.path.join(BASE_DIR, "paywatch.db"))


def _entitlement_conn(path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS crypto_entitlements (
            order_id TEXT PRIMARY KEY,
            plan_id TEXT NOT NULL,
            buyer_ref TEXT DEFAULT '',
            asset TEXT DEFAULT 'btc',
            txid TEXT,
            granted_at REAL NOT NULL
        )""")
    conn.commit()
    return conn


def list_entitlements(path: Optional[str] = None) -> list:
    path = path or db_path()
    if not os.path.exists(path):
        return []
    conn = _entitlement_conn(path)
    conn.row_factory = sqlite3.Row
    rows = [dict(r) for r in conn.execute(
        "SELECT * FROM crypto_entitlements ORDER BY granted_at DESC")]
    conn.close()
    return rows


def grant_entitlement(order, tx) -> None:
    """paywatch on_unlock callback: record that this order is paid.

    Runs for both watcher-matched unlocks and owner manual approvals.
    Never raises into the watcher: a CRM side effect failing must not
    un-pay an order whose payment already confirmed on chain.
    """
    try:
        conn = _entitlement_conn(db_path())
        conn.execute(
            "INSERT OR REPLACE INTO crypto_entitlements "
            "(order_id, plan_id, buyer_ref, asset, txid, granted_at) "
            "VALUES (?,?,?,?,?,?)",
            (order.id, order.plan_id, order.buyer_ref or "",
             getattr(order, "asset", "btc"),
             (tx or {}).get("txid"), time.time()))
        conn.commit()
        conn.close()
    except Exception:
        pass
    ref = (order.buyer_ref or "").strip()
    if ref.startswith("lead:"):
        try:
            from . import db as crm_db
            lead_id = int(ref.split(":", 1)[1])
            if crm_db.get_lead(lead_id):
                crm_db.add_note(
                    lead_id,
                    f"Crypto payment confirmed for plan {order.plan_id} "
                    f"(order {order.id}, asset {getattr(order, 'asset', 'btc')}).")
        except Exception:
            pass


def build_watcher(fetcher=None, rate_fetcher=None, store=None, plans=None):
    """Construct a Watcher wired to Wholesale Stack's entitlement grant."""
    import sys
    if BASE_DIR not in sys.path:
        sys.path.insert(0, BASE_DIR)
    from paywatch import Watcher
    from paywatch.store import SQLiteStore
    return Watcher(
        plans=plans if plans is not None else plans_source(),
        store=store or SQLiteStore(db_path()),
        fetcher=fetcher,
        rate_fetcher=rate_fetcher,
        on_unlock=grant_entitlement,
    )


def get_watcher():
    """Process-wide watcher singleton (lazy, so app boot never does network)."""
    global _watcher
    if _test_watcher is not None:
        return _test_watcher
    if _watcher is None:
        with _watcher_lock:
            if _watcher is None:
                _watcher = build_watcher()
    return _watcher


def set_watcher_for_tests(watcher) -> None:
    """Test hook: swap in a watcher with mocked chain and price providers."""
    global _test_watcher
    _test_watcher = watcher


def watcher_error_payload(exc) -> dict:
    payload = {"error": str(exc)}
    if getattr(exc, "code", None):
        payload["code"] = exc.code
    if getattr(exc, "provider_errors", None):
        payload["provider_errors"] = exc.provider_errors
    return payload
