/* Wholesale Stack crypto checkout - Cloudflare Worker.
 *
 * Standalone JS port of crypto-payment-watcher (paywatch) for
 * Wholesale Stack, which is a Python FastAPI app and cannot run on
 * Cloudflare free. Invoice state lives in D1 (binding DB). A scheduled
 * cron trigger sweeps open invoices. No access code gate: this is a
 * public checkout. The only secret is the optional
 * PAYWATCH_CRON_SECRET, which gates owner manual approval when set.
 *
 * Routes:
 *   GET  / or /checkout      checkout page
 *   GET  /health
 *   GET  /api/assets         per-asset availability (live probes)
 *   GET  /api/plans          plans + pool sizes + placeholder flag
 *   POST /api/orders         {plan_id, payer_address, asset?, buyer_ref?}
 *   GET  /api/orders/:id
 *   POST /api/orders/:id/check
 *   POST /api/orders/:id/approve  {owner_secret?}
 *   POST /api/sweep
 *   GET  /api/entitlements
 */
import { CheckoutService, CheckoutError } from "./service.js";
import { D1Store } from "./store.js";
import { publicOrder, supportedAssets, getAsset } from "./core.js";
import { checkoutPage } from "./page.js";

function json(obj, status = 200) {
  return new Response(JSON.stringify(obj), {
    status, headers: { "Content-Type": "application/json" },
  });
}

function makeService(env) {
  if (!env.DB) {
    throw new CheckoutError(
      "D1 binding DB is not set on this Worker; bind the wholesale-checkout database as DB", 503);
  }
  return new CheckoutService({ store: new D1Store(env.DB), env });
}

async function handle(request, env) {
  const url = new URL(request.url);
  const p = url.pathname;
  try {
    if (p === "/health") return json({ ok: true, service: "wholesale-crypto-checkout" });
    if ((p === "/" || p === "/checkout") && request.method === "GET") {
      const svc = makeService(env);
      const assets = supportedAssets().map((key) => {
        const spec = getAsset(key);
        return { key, symbol: spec.symbol, name: spec.name,
          confirmations: spec.confirmations, pool_size: svc.poolFor(key).length };
      });
      const html = checkoutPage({
        plans: Object.values(svc.plans), assets,
        placeholder: svc.placeholderPricing(),
      });
      return new Response(html, { headers: { "Content-Type": "text/html; charset=utf-8" } });
    }
    const svc = makeService(env);
    if (p === "/api/plans" && request.method === "GET") {
      return json({
        plans: Object.values(svc.plans),
        placeholder_pricing: svc.placeholderPricing(),
        assets: supportedAssets().map((key) => ({
          asset: key, symbol: getAsset(key).symbol,
          required_confirmations: getAsset(key).confirmations,
          pool_size: svc.poolFor(key).length })),
        invoice_minutes: 60, tolerance_pct: 1.0,
      });
    }
    if (p === "/api/assets" && request.method === "GET") {
      return json({ assets: await svc.assetStatuses() });
    }
    if (p === "/api/orders" && request.method === "POST") {
      const body = await request.json().catch(() => ({}));
      if (!body.plan_id || !body.payer_address) {
        return json({ error: "plan_id and payer_address are required" }, 400);
      }
      const order = await svc.createOrder(body.plan_id, body.payer_address, {
        buyerRef: body.buyer_ref || "", asset: body.asset || "btc" });
      return json(publicOrder(order));
    }
    const m = p.match(/^\/api\/orders\/([a-z0-9]+)(\/check|\/approve)?$/);
    if (m) {
      const [, id, action] = m;
      if (!action && request.method === "GET") {
        const order = await svc.getOrder(id);
        if (!order) return json({ error: `unknown order: ${id}` }, 404);
        return json(publicOrder(order));
      }
      if (action === "/check" && request.method === "POST") {
        return json(await svc.checkOrder(id));
      }
      if (action === "/approve" && request.method === "POST") {
        const body = await request.json().catch(() => ({}));
        return json(await svc.approveOrder(id, body.owner_secret || null));
      }
    }
    if (p === "/api/sweep" && request.method === "POST") {
      return json(await svc.sweep());
    }
    if (p === "/api/entitlements" && request.method === "GET") {
      return json({ entitlements: await svc.store.listEntitlements() });
    }
    return json({ error: "not found" }, 404);
  } catch (e) {
    if (e instanceof CheckoutError) {
      const payload = { error: e.message };
      if (e.code) payload.code = e.code;
      if (e.provider_errors && e.provider_errors.length) payload.provider_errors = e.provider_errors;
      return json(payload, e.status);
    }
    return json({ error: String(e && e.message || e) }, 500);
  }
}

export default {
  fetch: handle,
  async scheduled(_event, env, ctx) {
    const svc = makeService(env);
    ctx.waitUntil(svc.sweep());
  },
};
