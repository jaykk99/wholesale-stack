/* Checkout service: mirrors paywatch watcher.py order flow. */
import {
  ASSETS, getAsset, supportedAssets, loadPlans, loadPools,
  plansArePlaceholder, usdToAmount, matchPayment, publicOrder,
  validAddress, newOrderId, INVOICE_MINUTES,
} from "./core.js";
import { PriceFetcher, buildChainFetcher, AllProvidersUnavailable } from "./providers.js";

export class CheckoutError extends Error {
  constructor(message, status = 400, code = null, providerErrors = []) {
    super(message);
    this.status = status; this.code = code; this.provider_errors = providerErrors;
  }
}

export function assetUnavailable(spec, providerErrors) {
  return new CheckoutError(
    `${spec.symbol} payments are too busy right now. Please pick another crypto.`,
    503, "ASSET_UNAVAILABLE", providerErrors || []);
}

function errorDicts(exc) {
  if (exc instanceof AllProvidersUnavailable) return exc.errors;
  if (exc && exc.asDict) return [exc.asDict()];
  return [{ provider: "unknown", kind: "bad_response", status: null, error: String(exc && exc.message || exc).slice(0, 300) }];
}

export class CheckoutService {
  constructor({ store, env = {}, priceFetcher = null, chainFetchers = {}, fetchFn = fetch, nowFn = () => new Date() }) {
    this.store = store;
    this.env = env;
    this.plans = loadPlans(env);
    this.pools = loadPools(env);
    this.priceFetcher = priceFetcher || new PriceFetcher(fetchFn);
    this.chainFetchers = { ...chainFetchers };
    this.fetchFn = fetchFn;
    this.nowFn = nowFn;
    this.healthCache = new Map();
    // Entitlement hook: default records into the store. Host code can
    // replace onUnlock to grant something else; the Worker uses the
    // default, which is the D1 entitlements table (the paid flag).
    this.onUnlock = async (order, tx) => {
      await this.store.saveEntitlement({
        order_id: order.id, plan_id: order.plan_id,
        buyer_ref: order.buyer_ref || "", asset: order.asset,
        txid: tx ? tx.txid : null, granted_at: Math.floor(Date.now() / 1000),
      });
    };
  }

  poolFor(asset) { return [...(this.pools[asset] || [])]; }
  placeholderPricing() { return plansArePlaceholder(this.plans); }

  getChainFetcher(asset) {
    if (!this.chainFetchers[asset]) {
      this.chainFetchers[asset] = buildChainFetcher(asset, this.fetchFn);
    }
    return this.chainFetchers[asset];
  }

  async priceQuote(asset, injectedRate) {
    const spec = getAsset(asset);
    if (injectedRate !== undefined && injectedRate !== null) {
      if (!(injectedRate > 0)) throw assetUnavailable(spec, []);
      return { rate_usd: Number(injectedRate), provider: "injected", stale: false };
    }
    try {
      return await this.priceFetcher.rateInfo(spec);
    } catch (e) {
      throw assetUnavailable(spec, errorDicts(e));
    }
  }

  async chainHealth(asset) {
    const fetcher = this.getChainFetcher(asset);
    try {
      if (fetcher.health) { const p = await fetcher.health(); return { provider: String(p), errors: [] }; }
      const pool = this.poolFor(asset);
      const result = await fetcher.fetchAddress(pool[0] || "");
      return { provider: result.provider || fetcher.name || "chain-provider", errors: result.errors || [] };
    } catch (e) {
      return { provider: null, errors: errorDicts(e) };
    }
  }

  async assetStatus(asset) {
    const spec = getAsset(asset);
    const cached = this.healthCache.get(asset);
    if (cached && Date.now() - cached.at < 30_000) return { ...cached.value };
    const pool = this.poolFor(asset);
    const base = {
      asset, symbol: spec.symbol, name: spec.name, amount_unit: spec.unit,
      decimals: spec.decimals, required_confirmations: spec.confirmations,
      pool_size: pool.length, checkout_open: pool.length > 0,
      available: false, code: null, reason: null, message: null,
      price_usd: null, price_stale: false, price_provider: null,
      chain_provider: null, provider_errors: [],
    };
    if (!pool.length) {
      base.code = "CHECKOUT_CLOSED"; base.reason = "no_receive_addresses";
      base.message = `${spec.symbol} checkout is closed: no receive addresses are configured.`;
      this.healthCache.set(asset, { at: Date.now(), value: { ...base } });
      return base;
    }
    try {
      const quote = await this.priceQuote(asset);
      base.price_usd = quote.rate_usd; base.price_stale = quote.stale;
      base.price_provider = quote.provider;
    } catch (e) {
      base.code = "ASSET_UNAVAILABLE"; base.reason = "price_unavailable";
      base.message = e.message; base.provider_errors = e.provider_errors || [];
      this.healthCache.set(asset, { at: Date.now(), value: { ...base } });
      return base;
    }
    const health = await this.chainHealth(asset);
    base.provider_errors = health.errors;
    if (!health.provider) {
      base.code = "ASSET_UNAVAILABLE"; base.reason = "chain_unavailable";
      base.message = `${spec.symbol} payments are too busy right now. Please pick another crypto.`;
    } else {
      base.available = true; base.chain_provider = health.provider;
    }
    this.healthCache.set(asset, { at: Date.now(), value: { ...base } });
    return base;
  }

  async assetStatuses() {
    const out = [];
    for (const asset of supportedAssets()) out.push(await this.assetStatus(asset));
    return out;
  }

  async selectReceiveAddress(asset) {
    const pool = this.poolFor(asset);
    const counts = await this.store.activeCounts(asset);
    const minimum = Math.min(...pool.map((a) => counts.get(a) || 0));
    const tied = pool.filter((a) => (counts.get(a) || 0) === minimum);
    if (tied.length === 1) return tied[0];
    const name = `pool_rotation:${asset}`;
    const counter = await this.store.getCounter(name);
    await this.store.setCounter(name, counter + 1);
    return tied[counter % tied.length];
  }

  async createOrder(planId, payerAddress, { buyerRef = "", asset = "btc", rateUsd = null } = {}) {
    const spec = getAsset(asset);
    const pool = this.poolFor(spec.key);
    if (!pool.length) {
      throw new CheckoutError(
        `checkout closed: no ${spec.symbol} receive addresses are configured`,
        503, "CHECKOUT_CLOSED");
    }
    const plan = this.plans[planId];
    if (!plan) throw new CheckoutError(`unknown plan: ${planId}`, 404);
    if (!validAddress(spec.key, payerAddress)) {
      throw new CheckoutError(`payer address is not a valid ${spec.symbol} address`, 400);
    }
    const quote = await this.priceQuote(spec.key, rateUsd);
    const health = await this.chainHealth(spec.key);
    if (!health.provider) throw assetUnavailable(spec, health.errors);
    const now = this.nowFn();
    const order = {
      id: newOrderId(),
      plan_id: plan.id, price_usd: plan.price_usd,
      payer_address: String(payerAddress).trim(),
      receive_address: await this.selectReceiveAddress(spec.key),
      expected_amount: usdToAmount(plan.price_usd, quote.rate_usd, spec.decimals).toString(),
      created_at: now.toISOString(),
      expires_at: new Date(now.getTime() + INVOICE_MINUTES * 60_000).toISOString(),
      status: "pending", buyer_ref: buyerRef || "",
      seen_amount: "0", seen_txid: null, txid: null, tx_received_amount: "0",
      confirmations: 0, paid_at: null, late_payment_note: null,
      asset: spec.key, required_confirmations: spec.confirmations,
      provider: health.provider, provider_error: null, last_checked_at: null,
    };
    await this.store.save(order);
    return order;
  }

  async getOrder(orderId) { return this.store.get(orderId); }

  async unlock(order, tx, now) {
    order.status = "paid";
    order.paid_at = now.toISOString();
    order.txid = tx.txid;
    order.tx_received_amount = String(tx.received_amount);
    order.confirmations = tx.confirmations;
    await this.store.save(order);
    await this.onUnlock(order, tx);
  }

  async checkOrder(orderId, now = null) {
    now = now || this.nowFn();
    const order = await this.store.get(orderId);
    if (!order) throw new CheckoutError(`unknown order: ${orderId}`, 404);
    if (["paid", "manually_approved", "paid_late"].includes(order.status)) {
      return { action: "already_paid", order: publicOrder(order) };
    }
    const fetcher = this.getChainFetcher(order.asset);
    const expired = order.expires_at && now > new Date(order.expires_at);
    let fetched;
    try {
      fetched = await fetcher.fetchAddress(order.receive_address);
    } catch (e) {
      const errors = errorDicts(e);
      order.provider_error = String(e && e.message || e).slice(0, 500);
      order.last_checked_at = now.toISOString();
      await this.store.save(order);
      return { action: "explorer_error", error: order.provider_error,
        error_kind: errors[0] ? errors[0].kind : "bad_response",
        provider_errors: errors, order: publicOrder(order) };
    }
    const txs = Array.isArray(fetched) ? fetched : fetched.txs;
    const providerName = Array.isArray(fetched) ? (fetcher.name || null) : fetched.provider;
    const providerErrors = Array.isArray(fetched) ? [] : (fetched.errors || []);
    order.last_checked_at = now.toISOString();
    order.provider = providerName;
    order.provider_error = providerErrors.length
      ? providerErrors.map((e) => e.error || String(e)).join("; ").slice(0, 500) : null;

    const res = matchPayment(txs, order);
    if (res.bestSeenAmount > BigInt(order.seen_amount || "0")) {
      order.seen_amount = res.bestSeenAmount.toString();
    }
    if (res.bestSeenTxid) order.seen_txid = res.bestSeenTxid;
    const cand = res.match;
    if (cand) {
      order.confirmations = cand.confirmations;
      if (cand.confirmations >= order.required_confirmations) {
        if (expired) {
          order.status = "paid_late";
          order.late_payment_note = `qualifying tx ${cand.txid} confirmed after invoice expiry; owner manual resolution required`;
          await this.store.save(order);
          return { action: "paid_late", provider: providerName, provider_errors: providerErrors, order: publicOrder(order) };
        }
        const clash = await this.store.txidClaimedBy(cand.txid, order.id);
        if (clash !== null && clash !== undefined) {
          order.status = "underpaid";
          order.late_payment_note = `tx ${cand.txid} already claimed by another purchase; not reused`;
          await this.store.save(order);
          return { action: "txid_reused", provider: providerName, provider_errors: providerErrors, order: publicOrder(order) };
        }
        await this.unlock(order, cand, now);
        return { action: "unlocked", provider: providerName, provider_errors: providerErrors, order: publicOrder(order) };
      }
      if (order.asset === "sol") {
        order.status = "pending";
        await this.store.save(order);
        return { action: "pending", provider: providerName, provider_errors: providerErrors, order: publicOrder(order) };
      }
      order.status = "confirming";
      await this.store.save(order);
      return { action: "confirming", provider: providerName, provider_errors: providerErrors, order: publicOrder(order) };
    }
    if (expired) {
      order.status = "expired";
      await this.store.save(order);
      return { action: "expired", provider: providerName, provider_errors: providerErrors, order: publicOrder(order) };
    }
    if (BigInt(order.seen_amount || "0") > 0n) {
      order.status = "underpaid";
      await this.store.save(order);
      return { action: "underpaid", provider: providerName, provider_errors: providerErrors, order: publicOrder(order) };
    }
    order.status = "pending";
    await this.store.save(order);
    return { action: "pending", provider: providerName, provider_errors: providerErrors, order: publicOrder(order) };
  }

  async sweep(now = null) {
    now = now || this.nowFn();
    const counts = { checked: 0, unlocked: 0, confirming: 0, underpaid: 0,
      pending: 0, expired: 0, paid_late: 0, errors: 0 };
    const providerErrors = [];
    for (const order of await this.store.allOpen()) {
      counts.checked += 1;
      try {
        const res = await this.checkOrder(order.id, now);
        if (res.action === "explorer_error") {
          counts.errors += 1; providerErrors.push(...(res.provider_errors || []));
        } else if (res.action in counts) counts[res.action] += 1;
        providerErrors.push(...((res.provider_errors || []).filter((e) => !providerErrors.includes(e))));
      } catch { counts.errors += 1; }
    }
    return { watcher_enabled: true, provider_errors: providerErrors, ...counts };
  }

  async approveOrder(orderId, ownerSecret = null, now = null) {
    const required = (this.env.PAYWATCH_CRON_SECRET || "").trim();
    if (required && ownerSecret !== required) {
      throw new CheckoutError("owner approval denied", 403);
    }
    now = now || this.nowFn();
    const order = await this.store.get(orderId);
    if (!order) throw new CheckoutError(`unknown order: ${orderId}`, 404);
    if (["paid", "manually_approved"].includes(order.status)) {
      return { action: "already_paid", order: publicOrder(order) };
    }
    order.status = "manually_approved";
    order.paid_at = now.toISOString();
    await this.store.save(order);
    await this.onUnlock(order, { txid: order.txid, received_amount: order.tx_received_amount, confirmations: order.confirmations });
    return { action: "manually_approved", order: publicOrder(order) };
  }
}

export { ASSETS };
