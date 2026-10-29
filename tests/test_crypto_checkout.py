"""Crypto checkout routes: mocked chain and price providers, no network.

Covers invoice creation against the shipped default receive pools,
the unlock flow recording a Wholesale Stack entitlement, the honest
ASSET_UNAVAILABLE busy state, placeholder pricing detection, and the
checkout page warning. Chain tx shapes mirror the paywatch suite.
"""
import os
import sys
import tempfile

_tmp = tempfile.mkdtemp()
os.environ.setdefault("SQLITE_PATH", os.path.join(_tmp, "ws.db"))
os.environ.pop("SUPABASE_URL", None)
os.environ.pop("SUPABASE_KEY", None)
os.environ["WHOLESALE_CRYPTO_DB"] = os.path.join(_tmp, "paywatch.db")
os.environ["AUTOMATION"] = "0"
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app import crypto_checkout  # noqa: E402
from app.main import app  # noqa: E402
from paywatch import MemoryStore  # noqa: E402
from paywatch.providers import PriceQuote, ProviderError  # noqa: E402
import time  # noqa: E402

PAYER = "bc1qar0srrr7xfkvy5l643lydnw9re59gtzzwf5mdq"  # BIP-173 test vector
PLANS = [{"id": "starter", "name": "Starter", "price_usd": 19},
         {"id": "pro", "name": "Pro", "price_usd": 49}]
DEFAULT_BTC = "bc1qytghmmh90apq3w4uwsle97cjrhlq7etajju3t4"


class FakeFetcher:
    def __init__(self, txs=None, tip=100):
        self.txs = list(txs or [])
        self.tip = tip

    def address_txs(self, _addr):
        return self.txs

    def tip_height(self):
        return self.tip


class BrokenFetcher:
    name = "broken"

    def address_txs(self, _addr):
        raise ProviderError("broken", "unreachable", "down")

    def tip_height(self):
        raise ProviderError("broken", "unreachable", "down")


class FakePrice:
    def __init__(self, rate=19000.0):
        self.rate = rate

    def rate_info(self, _asset):
        return PriceQuote(self.rate, "fake-price", False, time.time())


def btc_tx(txid, to_receive, receive, conf_height=99):
    return {
        "txid": txid,
        "vout": [{"value": to_receive, "scriptpubkey_address": receive}],
        "vin": [{"prevout": {"scriptpubkey_address": PAYER}}],
        "status": {"confirmed": conf_height is not None,
                   "block_height": conf_height},
    }


@pytest.fixture()
def client_and_chain():
    chain = FakeFetcher()
    watcher = crypto_checkout.build_watcher(
        fetcher=chain, rate_fetcher=FakePrice(), store=MemoryStore(), plans=PLANS)
    crypto_checkout.set_watcher_for_tests(watcher)
    yield TestClient(app), chain, watcher
    crypto_checkout.set_watcher_for_tests(None)


def test_plans_endpoint_and_placeholder_file():
    data = crypto_checkout.plans_source()
    import paywatch.core as core
    plans = core.load_plans(data)
    assert crypto_checkout.plans_are_placeholder(plans) is True
    assert all(p.price_usd == 1 for p in plans.values())


def test_create_order_pins_amount_and_uses_default_pool(client_and_chain):
    client, _chain, _w = client_and_chain
    r = client.post("/api/crypto/orders", json={
        "plan_id": "starter", "payer_address": PAYER, "asset": "btc"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["expected_sats"] == 100_000  # $19 at fake $19,000/BTC
    assert body["receive_address"] == DEFAULT_BTC
    assert body["status"] == "pending"
    assert body["required_confirmations"] == 2


def test_unlock_records_entitlement(client_and_chain):
    client, chain, _w = client_and_chain
    r = client.post("/api/crypto/orders", json={
        "plan_id": "starter", "payer_address": PAYER,
        "buyer_ref": "buyer-1", "asset": "btc"})
    order = r.json()
    res = client.post(f"/api/crypto/orders/{order['id']}/check")
    assert res.json()["action"] == "pending"
    chain.txs = [btc_tx("tx-unlock-1", 100_000, order["receive_address"])]
    res = client.post(f"/api/crypto/orders/{order['id']}/check")
    assert res.json()["action"] == "unlocked", res.text
    got = client.get(f"/api/crypto/orders/{order['id']}")
    assert got.json()["status"] == "paid"
    ents = crypto_checkout.list_entitlements()
    assert any(e["order_id"] == order["id"] and e["plan_id"] == "starter"
               and e["txid"] == "tx-unlock-1" for e in ents)
    api_ents = client.get("/api/crypto/entitlements").json()["entitlements"]
    assert any(e["order_id"] == order["id"] for e in api_ents)


def test_underpayment_does_not_unlock(client_and_chain):
    client, chain, _w = client_and_chain
    order = client.post("/api/crypto/orders", json={
        "plan_id": "starter", "payer_address": PAYER, "asset": "btc"}).json()
    chain.txs = [btc_tx("tx-under", 50_000, order["receive_address"])]
    res = client.post(f"/api/crypto/orders/{order['id']}/check")
    assert res.json()["action"] == "underpaid"
    assert client.get(f"/api/crypto/orders/{order['id']}").json()["status"] == "underpaid"


def test_asset_unavailable_when_chain_down():
    watcher = crypto_checkout.build_watcher(
        fetcher=BrokenFetcher(), rate_fetcher=FakePrice(),
        store=MemoryStore(), plans=PLANS)
    crypto_checkout.set_watcher_for_tests(watcher)
    try:
        client = TestClient(app, raise_server_exceptions=False)
        r = client.post("/api/crypto/orders", json={
            "plan_id": "starter", "payer_address": PAYER, "asset": "btc"})
        assert r.status_code == 503, r.text
        assert r.json()["code"] == "ASSET_UNAVAILABLE"
    finally:
        crypto_checkout.set_watcher_for_tests(None)


def test_unknown_plan_and_bad_payer(client_and_chain):
    client, _chain, _w = client_and_chain
    r = client.post("/api/crypto/orders", json={
        "plan_id": "nope", "payer_address": PAYER, "asset": "btc"})
    assert r.status_code == 404
    r = client.post("/api/crypto/orders", json={
        "plan_id": "starter", "payer_address": "not-an-address", "asset": "btc"})
    assert r.status_code == 400
    r = client.get("/api/crypto/orders/does-not-exist")
    assert r.status_code == 404


def test_checkout_page_shows_placeholder_warning(client_and_chain):
    client, _chain, _w = client_and_chain
    # Swap in the shipped placeholder plans for the page check.
    watcher = crypto_checkout.build_watcher(
        fetcher=FakeFetcher(), rate_fetcher=FakePrice(), store=MemoryStore())
    crypto_checkout.set_watcher_for_tests(watcher)
    r = client.get("/checkout")
    assert r.status_code == 200
    assert "Pricing is not set yet" in r.text
    assert "PLACEHOLDER" in r.text
