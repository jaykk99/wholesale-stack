/* Offline tests for the Cloudflare checkout port. Mocked providers only. */
import { test } from "node:test";
import assert from "node:assert/strict";

import {
  usdToAmount, thresholdAmount, matchPayment, loadPools, loadPlans,
  plansArePlaceholder, validAddress, DEFAULT_ADDRESSES,
} from "../src/core.js";
import { PriceFetcher, ProviderError } from "../src/providers.js";
import { CheckoutService, CheckoutError } from "../src/service.js";
import { MemoryStore, D1Store } from "../src/store.js";
import { FakeD1 } from "./fake-d1.mjs";
import worker from "../src/worker.js";

const PAYER = "bc1qar0srrr7xfkvy5l643lydnw9re59gtzzwf5mdq";
const EVM_PAYER = "0x1111111111111111111111111111111111111111";
const EVM_RECEIVE = DEFAULT_ADDRESSES.eth[0];
const SOL_PAYER = "4wBqpZM9xaSheZzJSMawUKKwhdpChKbZ5eu5ky4Vigw";
const PLANS = [
  { id: "starter", name: "Starter", price_usd: 19 },
  { id: "pro", name: "Pro", price_usd: 49 },
];
const ENV = { PAYWATCH_PLANS_JSON: JSON.stringify({ plans: PLANS }) };

class FakePrice {
  constructor(rate = 19000) { this.rate = rate; }
  async rateInfo() { return { rate_usd: this.rate, provider: "fake-price", stale: false }; }
}
class FakeChain {
  constructor(txs = [], name = "fake-chain") { this.txs = txs; this.name = name; }
  async fetchAddress() { return { txs: this.txs, tip_height: 100, provider: this.name, errors: [] }; }
  async health() { return this.name; }
}
class BrokenChain {
  constructor() { this.name = "broken"; }
  async fetchAddress() { throw new ProviderError("broken", "unreachable", "down"); }
  async health() { throw new ProviderError("broken", "unreachable", "down"); }
}
function btcTx(txid, value, receive, conf = 2, payer = PAYER) {
  return { txid, from_addresses: [payer], to_address: receive,
    value_amount: String(value), confirmations: conf };
}
function makeService(chain, store = new MemoryStore(), price = new FakePrice()) {
  return new CheckoutService({
    store, env: ENV, priceFetcher: price,
    chainFetchers: { btc: chain, eth: chain, bnb: chain, sol: chain },
  });
}

test("amount pinning and tolerance use exact integer math", () => {
  assert.equal(usdToAmount(19, 19000, 8), 100000n);
  assert.equal(usdToAmount(19, 1900, 18), 10000000000000000n);
  assert.equal(thresholdAmount(100000n), 99000n);
  assert.equal(thresholdAmount("101"), 100n);
});

test("validators", () => {
  assert.ok(validAddress("btc", PAYER));
  assert.ok(validAddress("eth", EVM_PAYER));
  assert.ok(validAddress("bnb", EVM_PAYER));
  assert.ok(validAddress("sol", SOL_PAYER));
  assert.ok(!validAddress("eth", "0x1234"));
  assert.ok(!validAddress("btc", "not-an-address"));
});

test("default pools ship the public receive addresses, env overrides per asset", () => {
  const pools = loadPools({});
  assert.deepEqual(pools.btc, DEFAULT_ADDRESSES.btc);
  assert.deepEqual(pools.eth, DEFAULT_ADDRESSES.eth);
  assert.deepEqual(pools.sol, DEFAULT_ADDRESSES.sol);
  const overridden = loadPools({ PAYWATCH_BTC_ADDRESSES: "btc-custom" });
  assert.deepEqual(overridden.btc, ["btc-custom"]);
  assert.deepEqual(overridden.eth, DEFAULT_ADDRESSES.eth);
  const closed = loadPools({ PAYWATCH_ADDRESSES: JSON.stringify({ btc: [] }) });
  assert.deepEqual(closed.btc, []);
});

test("placeholder plans are the default and are flagged", () => {
  const plans = loadPlans({});
  assert.ok(plansArePlaceholder(plans));
  assert.ok(Object.values(plans).every((p) => p.price_usd === 1));
});

test("matcher enforces payer binding, recipient, threshold", () => {
  const order = { asset: "btc", payer_address: PAYER,
    receive_address: DEFAULT_ADDRESSES.btc[0], expected_amount: "100000" };
  const wrong = matchPayment([btcTx("a", 100000, order.receive_address, 2, "someone-else")], order);
  assert.equal(wrong.match, null);
  assert.equal(wrong.bestSeenAmount, 0n);
  const under = matchPayment([btcTx("b", 50000, order.receive_address)], order);
  assert.equal(under.match, null);
  assert.equal(under.bestSeenAmount, 50000n);
  const good = matchPayment([btcTx("c", 100000, order.receive_address)], order);
  assert.equal(good.match.txid, "c");
  assert.equal(good.match.confirmations, 2);
});

test("BTC invoice creates, confirms, unlocks, records entitlement", async () => {
  const chain = new FakeChain();
  const svc = makeService(chain);
  const order = await svc.createOrder("starter", PAYER, { asset: "btc" });
  assert.equal(order.expected_amount, "100000");
  assert.equal(order.receive_address, DEFAULT_ADDRESSES.btc[0]);
  assert.equal(order.required_confirmations, 2);
  let res = await svc.checkOrder(order.id);
  assert.equal(res.action, "pending");
  chain.txs = [btcTx("tx1", 100000, order.receive_address, 1)];
  res = await svc.checkOrder(order.id);
  assert.equal(res.action, "confirming");
  chain.txs = [btcTx("tx1", 100000, order.receive_address, 2)];
  res = await svc.checkOrder(order.id);
  assert.equal(res.action, "unlocked");
  assert.equal((await svc.getOrder(order.id)).status, "paid");
  const ents = await svc.store.listEntitlements();
  assert.equal(ents.length, 1);
  assert.equal(ents[0].txid, "tx1");
});

test("single-use txid: second order cannot reuse a claimed tx", async () => {
  const chain = new FakeChain();
  const svc = makeService(chain);
  const o1 = await svc.createOrder("starter", PAYER, { asset: "btc" });
  chain.txs = [btcTx("shared", 100000, o1.receive_address, 5)];
  assert.equal((await svc.checkOrder(o1.id)).action, "unlocked");
  const o2 = await svc.createOrder("starter", PAYER, { asset: "btc" });
  const res = await svc.checkOrder(o2.id);
  assert.equal(res.action, "txid_reused");
  assert.equal((await svc.getOrder(o2.id)).status, "underpaid");
});

test("qualifying payment after expiry is paid_late, never unlocked", async () => {
  const chain = new FakeChain();
  const svc = makeService(chain);
  const order = await svc.createOrder("starter", PAYER, { asset: "btc" });
  chain.txs = [btcTx("late", 100000, order.receive_address, 5)];
  const after = new Date(Date.now() + 61 * 60_000);
  const res = await svc.checkOrder(order.id, after);
  assert.equal(res.action, "paid_late");
  assert.equal((await svc.getOrder(order.id)).status, "paid_late");
  assert.equal((await svc.store.listEntitlements()).length, 0);
});

test("ETH unlock needs 12 confirmations and wei amounts stay exact", async () => {
  const chain = new FakeChain();
  const svc = makeService(chain, new MemoryStore(), new FakePrice(1900));
  const order = await svc.createOrder("starter", EVM_PAYER, { asset: "eth" });
  assert.equal(order.expected_amount, "10000000000000000");
  assert.equal(order.required_confirmations, 12);
  const tx = (conf) => ({ txid: "0xabc", from_addresses: [EVM_PAYER],
    to_address: EVM_RECEIVE, value_amount: order.expected_amount, confirmations: conf });
  chain.txs = [tx(11)];
  assert.equal((await svc.checkOrder(order.id)).action, "confirming");
  chain.txs = [tx(12)];
  assert.equal((await svc.checkOrder(order.id)).action, "unlocked");
});

test("SOL unlocks only when finalized", async () => {
  const chain = new FakeChain();
  const svc = makeService(chain, new MemoryStore(), new FakePrice(100));
  const order = await svc.createOrder("starter", SOL_PAYER, { asset: "sol" });
  assert.equal(order.required_confirmations, 1);
  chain.txs = [{ txid: "sig1", from_addresses: [SOL_PAYER],
    to_address: order.receive_address, value_amount: order.expected_amount,
    confirmations: 0, finalized: false }];
  assert.equal((await svc.checkOrder(order.id)).action, "pending");
  chain.txs = [{ txid: "sig1", from_addresses: [SOL_PAYER],
    to_address: order.receive_address, value_amount: order.expected_amount,
    confirmations: 1, finalized: true }];
  assert.equal((await svc.checkOrder(order.id)).action, "unlocked");
});

test("chain down at creation returns ASSET_UNAVAILABLE 503", async () => {
  const svc = makeService(new BrokenChain());
  await assert.rejects(
    () => svc.createOrder("starter", PAYER, { asset: "btc" }),
    (e) => e instanceof CheckoutError && e.status === 503 && e.code === "ASSET_UNAVAILABLE");
  const status = await svc.assetStatus("btc");
  assert.equal(status.available, false);
  assert.equal(status.code, "ASSET_UNAVAILABLE");
});

test("price failover: coingecko down, coinbase answers", async () => {
  const fetchFn = async (url) => {
    if (url.includes("coingecko")) return { ok: false, status: 429, json: async () => ({}) };
    if (url.includes("coinbase")) return { ok: true, status: 200, json: async () => ({ data: { amount: "20000" } }) };
    throw new Error("unexpected url " + url);
  };
  const pf = new PriceFetcher(fetchFn);
  const quote = await pf.rateInfo({ key: "btc", priceId: "bitcoin", coinbase: "BTC-USD", kraken: "XBTUSD" });
  assert.equal(quote.rate_usd, 20000);
  assert.equal(quote.provider, "coinbase");
});

test("D1 store roundtrip through the service", async () => {
  const chain = new FakeChain();
  const svc = new CheckoutService({
    store: new D1Store(new FakeD1()), env: ENV, priceFetcher: new FakePrice(),
    chainFetchers: { btc: chain },
  });
  const order = await svc.createOrder("starter", PAYER, { asset: "btc" });
  chain.txs = [btcTx("d1tx", 100000, order.receive_address, 3)];
  assert.equal((await svc.checkOrder(order.id)).action, "unlocked");
  const ents = await svc.store.listEntitlements();
  assert.equal(ents.length, 1);
});

test("worker routes: plans, create, check, sweep, page", async () => {
  const env = { DB: new FakeD1(), ...ENV };
  // Live providers are not mocked at the worker layer, so exercise the
  // offline routes only: plans, page, health, unknown order.
  let res = await worker.fetch(new Request("https://x/health"), env);
  assert.equal(res.status, 200);
  res = await worker.fetch(new Request("https://x/api/plans"), env);
  const plans = await res.json();
  assert.equal(plans.placeholder_pricing, false);
  assert.equal(plans.plans.length, 2);
  res = await worker.fetch(new Request("https://x/"), env);
  assert.equal(res.status, 200);
  assert.match(await res.text(), /Crypto checkout/);
  res = await worker.fetch(new Request("https://x/api/orders/nope"), env);
  assert.equal(res.status, 404);
});

test("worker page hides prices in placeholder mode", async () => {
  const env = { DB: new FakeD1() };
  const res = await worker.fetch(new Request("https://x/checkout"), env);
  const html = await res.text();
  assert.match(html, /Pricing is not set yet/);
  assert.ok(!html.includes("$1.00"));
});

test("manual approve records entitlement and respects the secret", async () => {
  const svc = makeService(new FakeChain());
  const order = await svc.createOrder("starter", PAYER, { asset: "btc" });
  const res = await svc.approveOrder(order.id);
  assert.equal(res.action, "manually_approved");
  assert.equal((await svc.store.listEntitlements()).length, 1);
  const gated = new CheckoutService({
    store: new MemoryStore(),
    env: { ...ENV, PAYWATCH_CRON_SECRET: "s3cret" },
    priceFetcher: new FakePrice(), chainFetchers: { btc: new FakeChain() },
  });
  const o2 = await gated.createOrder("starter", PAYER, { asset: "btc" });
  await assert.rejects(() => gated.approveOrder(o2.id, "wrong"),
    (e) => e instanceof CheckoutError && e.status === 403);
});
