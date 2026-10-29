/* Pure core for the Wholesale Stack crypto checkout Worker.
 * Mirrors crypto-payment-watcher (paywatch) rules:
 * 60 minute invoice window, 1 percent tolerance, payer binding,
 * single-use txid, per-asset confirmations, paid_late never unlocks.
 * Amounts are BigInt smallest units (sats, wei, lamports) everywhere.
 */

export const INVOICE_MINUTES = 60;
export const TOLERANCE_PCT = 1.0;

export const DEFAULT_ADDRESSES = {
  btc: ["bc1qytghmmh90apq3w4uwsle97cjrhlq7etajju3t4"],
  eth: ["0x689Bc15555982E5bD01240416F2aB5a6cebb196f"],
  bnb: ["0x689Bc15555982E5bD01240416F2aB5a6cebb196f"],
  sol: ["HhH3fBgYNDFBuXZZxcEogqHU64Ta15zXo5TzezGJqhX9"],
};

export const ASSETS = {
  btc: { key: "btc", symbol: "BTC", name: "Bitcoin", priceId: "bitcoin",
    coinbase: "BTC-USD", kraken: "XBTUSD", decimals: 8, unit: "sats",
    confirmations: 2, family: "utxo" },
  eth: { key: "eth", symbol: "ETH", name: "Ethereum", priceId: "ethereum",
    coinbase: "ETH-USD", kraken: "ETHUSD", decimals: 18, unit: "wei",
    confirmations: 12, family: "account",
    blockscout: "https://eth.blockscout.com" },
  bnb: { key: "bnb", symbol: "BNB", name: "BNB Chain", priceId: "binancecoin",
    coinbase: "BNB-USD", kraken: "BNBUSD", decimals: 18, unit: "wei",
    confirmations: 15, family: "account",
    blockscout: "https://bsc.blockscout.com" },
  sol: { key: "sol", symbol: "SOL", name: "Solana", priceId: "solana",
    coinbase: "SOL-USD", kraken: "SOLUSD", decimals: 9, unit: "lamports",
    confirmations: 1, family: "solana-rpc" },
};

export function getAsset(key) {
  const spec = ASSETS[String(key || "btc").toLowerCase()];
  if (!spec) throw Object.assign(new Error(`unsupported asset: ${key}`),
    { status: 404, code: "ASSET_NOT_SUPPORTED" });
  return spec;
}

export function supportedAssets() { return Object.keys(ASSETS); }

const B58 = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz";
export function validBtcAddress(a) {
  if (!a || typeof a !== "string") return false;
  const s = a.trim();
  if (/^bc1[qpzry9x8gf2tvdw0s3jn54khce6mua7l]{11,71}$/.test(s)) return true;
  if (/^[13][a-km-zA-HJ-NP-Z1-9]{25,34}$/.test(s)) return true;
  return false;
}
export function validEthAddress(a) {
  return typeof a === "string" && /^0x[0-9a-fA-F]{40}$/.test(a.trim());
}
export function validSolAddress(a) {
  if (typeof a !== "string") return false;
  const s = a.trim();
  return s.length >= 32 && s.length <= 44 && [...s].every((c) => B58.includes(c));
}
export function validAddress(asset, a) {
  if (asset === "btc") return validBtcAddress(a);
  if (asset === "eth" || asset === "bnb") return validEthAddress(a);
  if (asset === "sol") return validSolAddress(a);
  return false;
}

/* Pin a USD price into smallest units, floored, with exact integer math.
 * price and rate are scaled by 1e8 so wei amounts stay precise. */
export function usdToAmount(priceUsd, rateUsd, decimals) {
  const priceScaled = BigInt(Math.round(Number(priceUsd) * 1e8));
  const rateScaled = BigInt(Math.round(Number(rateUsd) * 1e8));
  if (rateScaled <= 0n) throw new Error("asset rate must be positive");
  return (priceScaled * (10n ** BigInt(decimals))) / rateScaled;
}

export function thresholdAmount(expected) {
  const e = BigInt(expected);
  return e - e / 100n;
}

export function loadPlans(env) {
  let raw = (env && (env.PAYWATCH_PLANS_JSON || env.WHOLESALE_PLANS_JSON)) || "";
  let items = [];
  if (raw) {
    const data = JSON.parse(raw);
    items = Array.isArray(data) ? data : (data.plans || []);
  } else {
    items = PLACEHOLDER_PLANS;
  }
  const plans = {};
  for (const e of items) {
    plans[e.id] = { id: String(e.id), name: String(e.name || e.id),
      price_usd: Number(e.price_usd), duration_days: Number(e.duration_days || 30),
      features: e.features || [] };
  }
  if (!Object.keys(plans).length) throw new Error("no plans configured");
  return plans;
}

export const PLACEHOLDER_PLANS = [
  { id: "placeholder_access", name: "PLACEHOLDER Access (set a real name and price before selling)",
    price_usd: 1, duration_days: 30, features: ["PLACEHOLDER pricing, not a real offer"] },
  { id: "placeholder_pro", name: "PLACEHOLDER Pro (set a real name and price before selling)",
    price_usd: 1, duration_days: 30, features: ["PLACEHOLDER pricing, not a real offer"] },
];

export function plansArePlaceholder(plans) {
  return Object.keys(plans).some((id) => id.startsWith("placeholder"));
}

export function loadPools(env) {
  const pools = {};
  const mentioned = new Set();
  const raw = (env && env.PAYWATCH_ADDRESSES) || "";
  if (raw) {
    const parsed = JSON.parse(raw);
    for (const [k, v] of Object.entries(parsed)) {
      const key = k.toLowerCase();
      mentioned.add(key);
      pools[key] = (Array.isArray(v) ? v : [v]).map((s) => String(s).trim()).filter(Boolean);
    }
  }
  if (env) {
    for (const key of supportedAssets()) {
      const v = env[`PAYWATCH_${key.toUpperCase()}_ADDRESSES`];
      if (v) {
        mentioned.add(key);
        pools[key] = [...new Set([...(pools[key] || []),
          ...String(v).split(",").map((s) => s.trim()).filter(Boolean)])];
      }
    }
    if (env.PAYWATCH_BTC_ADDRESS) {
      mentioned.add("btc");
      pools.btc = [...new Set([...(pools.btc || []), env.PAYWATCH_BTC_ADDRESS.trim()])];
    }
  }
  for (const [key, values] of Object.entries(DEFAULT_ADDRESSES)) {
    if (!mentioned.has(key) && !(pools[key] && pools[key].length)) pools[key] = [...values];
  }
  return pools;
}

/* Match normalized chain txs against an order.
 * Normalized tx: { txid, from_addresses: [..] or from_address, to_address,
 * value_amount: string|bigint|number, confirmations, finalized }
 * Returns { match, bestSeenAmount (bigint), bestSeenTxid }. */
export function matchPayment(txs, order) {
  const threshold = thresholdAmount(order.expected_amount);
  const payer = order.payer_address.trim();
  const payerCmp = (order.asset === "eth" || order.asset === "bnb")
    ? payer.toLowerCase() : payer;
  let best = 0n, bestTxid = null, match = null;
  for (const tx of txs || []) {
    const to = String(tx.to_address || "");
    const toCmp = (order.asset === "eth" || order.asset === "bnb") ? to.toLowerCase() : to;
    const recvCmp = (order.asset === "eth" || order.asset === "bnb")
      ? order.receive_address.toLowerCase() : order.receive_address;
    if (toCmp !== recvCmp) continue;
    const froms = tx.from_addresses || (tx.from_address ? [tx.from_address] : []);
    const bound = froms.some((f) => {
      const fc = (order.asset === "eth" || order.asset === "bnb")
        ? String(f).toLowerCase() : String(f);
      return fc === payerCmp;
    });
    if (!bound) continue;
    const value = BigInt(tx.value_amount);
    if (value > best) { best = value; bestTxid = tx.txid; }
    if (value >= threshold) {
      const conf = order.asset === "sol"
        ? (tx.finalized ? 1 : 0) : Number(tx.confirmations || 0);
      const cand = { txid: tx.txid, received_amount: value.toString(),
        confirmations: conf };
      if (!match || cand.confirmations > match.confirmations) match = cand;
    }
  }
  return { match, bestSeenAmount: best, bestSeenTxid: bestTxid };
}

export function publicOrder(o) {
  const out = {
    id: o.id, asset: o.asset, symbol: o.asset.toUpperCase(),
    plan_id: o.plan_id, price_usd: o.price_usd, status: o.status,
    payer_address: o.payer_address, receive_address: o.receive_address,
    amount_unit: ASSETS[o.asset] ? ASSETS[o.asset].unit : "units",
    expected_amount: String(o.expected_amount),
    threshold_amount: thresholdAmount(o.expected_amount).toString(),
    seen_amount: String(o.seen_amount || "0"),
    txid: o.txid || null, seen_txid: o.seen_txid || null,
    confirmations: o.confirmations || 0,
    required_confirmations: o.required_confirmations,
    created_at: o.created_at, expires_at: o.expires_at,
    paid_at: o.paid_at || null, buyer_ref: o.buyer_ref || "",
    provider: o.provider || null, provider_error: o.provider_error || null,
    late_payment_note: o.late_payment_note || null,
  };
  if (o.asset === "btc") out.expected_sats = Number(o.expected_amount);
  if (o.asset === "eth" || o.asset === "bnb") out.expected_wei = String(o.expected_amount);
  if (o.asset === "sol") {
    out.expected_lamports = String(o.expected_amount);
    out.finalized = (o.confirmations || 0) >= o.required_confirmations;
  }
  return out;
}

export function newOrderId() {
  const bytes = new Uint8Array(8);
  crypto.getRandomValues(bytes);
  return [...bytes].map((b) => b.toString(16).padStart(2, "0")).join("");
}
