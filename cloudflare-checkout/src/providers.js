/* Keyless public providers with failover, mirroring paywatch providers.py.
 * Every fetcher is injectable (fetchFn) so tests run fully offline.
 * Provider errors carry a kind: rate_limited, unreachable, bad_response.
 */

export class ProviderError extends Error {
  constructor(provider, kind, message, status = null) {
    super(message);
    this.provider = provider; this.kind = kind; this.status = status;
  }
  asDict() { return { provider: this.provider, kind: this.kind, status: this.status, error: this.message }; }
}

export class AllProvidersUnavailable extends Error {
  constructor(errors, what = "provider") {
    super(`${what} unavailable on every provider`);
    this.errors = errors;
  }
}

function kindForStatus(status) {
  if (status === 429) return "rate_limited";
  if (status >= 400) return "bad_response";
  return "unreachable";
}

async function getJson(fetchFn, provider, url, options = {}) {
  let res;
  try {
    res = await fetchFn(url, options);
  } catch (e) {
    throw new ProviderError(provider, "unreachable", String(e && e.message || e));
  }
  if (!res.ok) {
    throw new ProviderError(provider, kindForStatus(res.status),
      `${provider} HTTP ${res.status}`, res.status);
  }
  try { return await res.json(); }
  catch { throw new ProviderError(provider, "bad_response", `${provider} returned non-JSON`); }
}

/* ------------------------------------------------------------- prices */

export class PriceFetcher {
  constructor(fetchFn = fetch, nowFn = () => Date.now()) {
    this.fetchFn = fetchFn; this.nowFn = nowFn;
    this.cache = new Map(); // asset -> {rate, provider, at}
    this.freshMs = 60_000; this.staleMs = 600_000;
  }
  async rateInfo(spec) {
    const cached = this.cache.get(spec.key);
    if (cached && this.nowFn() - cached.at < this.freshMs) {
      return { rate_usd: cached.rate, provider: cached.provider, stale: false };
    }
    const errors = [];
    const attempts = [
      ["coingecko", async () => {
        const data = await getJson(this.fetchFn, "coingecko",
          `https://api.coingecko.com/api/v3/simple/price?ids=${spec.priceId}&vs_currencies=usd`);
        const rate = data && data[spec.priceId] && data[spec.priceId].usd;
        if (!rate) throw new ProviderError("coingecko", "bad_response", "no usd rate in response");
        return Number(rate);
      }],
      ["coinbase", async () => {
        const data = await getJson(this.fetchFn, "coinbase",
          `https://api.coinbase.com/v2/prices/${spec.coinbase}/spot`);
        const rate = data && data.data && data.data.amount;
        if (!rate) throw new ProviderError("coinbase", "bad_response", "no amount in response");
        return Number(rate);
      }],
      ["kraken", async () => {
        const data = await getJson(this.fetchFn, "kraken",
          `https://api.kraken.com/0/public/Ticker?pair=${spec.kraken}`);
        const result = (data && data.result) || {};
        const first = Object.values(result)[0];
        const rate = first && first.c && first.c[0];
        if (!rate) throw new ProviderError("kraken", "bad_response", "no ticker in response");
        return Number(rate);
      }],
    ];
    for (const [name, fn] of attempts) {
      try {
        const rate = await fn();
        if (!(rate > 0)) throw new ProviderError(name, "bad_response", "non-positive rate");
        this.cache.set(spec.key, { rate, provider: name, at: this.nowFn() });
        return { rate_usd: rate, provider: name, stale: false };
      } catch (e) {
        errors.push(e instanceof ProviderError ? e.asDict()
          : new ProviderError(name, "unreachable", String(e)).asDict());
      }
    }
    if (cached && this.nowFn() - cached.at < this.staleMs) {
      return { rate_usd: cached.rate, provider: cached.provider, stale: true };
    }
    throw new AllProvidersUnavailable(errors, "price fetch");
  }
}

/* ------------------------------------------------------------- BTC */

export class EsploraFetcher {
  constructor(base, name, fetchFn = fetch) {
    this.base = base.replace(/\/$/, ""); this.name = name; this.fetchFn = fetchFn;
  }
  async tipHeight() {
    const res = await this.fetchFn(`${this.base}/blocks/tip/height`);
    if (!res.ok) throw new ProviderError(this.name, kindForStatus(res.status), `tip HTTP ${res.status}`, res.status);
    return Number(await res.text());
  }
  async fetchAddress(address) {
    const txsRaw = await getJson(this.fetchFn, this.name, `${this.base}/address/${address}/txs`);
    if (!Array.isArray(txsRaw)) throw new ProviderError(this.name, "bad_response", "txs not a list");
    let tip = null;
    try { tip = await this.tipHeight(); } catch { /* confirmations stay 0 */ }
    const txs = txsRaw.map((tx) => ({
      txid: tx.txid,
      from_addresses: (tx.vin || []).map((v) => v.prevout && v.prevout.scriptpubkey_address).filter(Boolean),
      to_address: address,
      value_amount: String((tx.vout || [])
        .filter((o) => o.scriptpubkey_address === address)
        .reduce((sum, o) => sum + Number(o.value || 0), 0)),
      confirmations: tx.status && tx.status.confirmed && tip && tx.status.block_height
        ? Math.max(tip - tx.status.block_height + 1, 0) : 0,
    })).filter((t) => BigInt(t.value_amount) > 0n);
    return { txs, tip_height: tip, provider: this.name, errors: [] };
  }
  async health() { await this.tipHeight(); return this.name; }
}

export class FailoverChainFetcher {
  constructor(fetchers) { this.fetchers = fetchers; this.name = fetchers.map((f) => f.name).join("+"); this.last_errors = []; }
  async fetchAddress(address) {
    const errors = [];
    for (const f of this.fetchers) {
      try {
        const result = await f.fetchAddress(address);
        this.last_errors = errors;
        return { ...result, errors: [...errors, ...(result.errors || [])] };
      } catch (e) {
        errors.push(e instanceof ProviderError ? e.asDict()
          : new ProviderError(f.name, "unreachable", String(e)).asDict());
      }
    }
    this.last_errors = errors;
    throw new AllProvidersUnavailable(errors, "chain fetch");
  }
  async health() {
    const errors = [];
    for (const f of this.fetchers) {
      try { return await f.health(); }
      catch (e) { errors.push(e instanceof ProviderError ? e.asDict() : { provider: f.name, kind: "unreachable", error: String(e) }); }
    }
    throw new AllProvidersUnavailable(errors, "chain health");
  }
}

export function btcFetcher(fetchFn = fetch) {
  return new FailoverChainFetcher([
    new EsploraFetcher("https://mempool.space/api", "mempool.space", fetchFn),
    new EsploraFetcher("https://blockstream.info/api", "blockstream.info", fetchFn),
  ]);
}

/* ------------------------------------------------------------- EVM */

export class BlockscoutFetcher {
  constructor(base, name, fetchFn = fetch) {
    this.base = base.replace(/\/$/, ""); this.name = name; this.fetchFn = fetchFn;
  }
  async fetchAddress(address) {
    const url = `${this.base}/api?module=account&action=txlist&address=${address}&sort=desc&page=1&offset=50`;
    const data = await getJson(this.fetchFn, this.name, url);
    if (!data || !Array.isArray(data.result)) {
      throw new ProviderError(this.name, "bad_response",
        `blockscout result not a list: ${data && data.message ? data.message : "unknown"}`);
    }
    const txs = data.result.filter((t) => String(t.isError || "0") !== "1").map((t) => ({
      txid: t.hash,
      from_addresses: [t.from],
      to_address: t.to,
      value_amount: String(t.value),
      confirmations: Number(t.confirmations || 0),
    }));
    return { txs, tip_height: null, provider: this.name, errors: [] };
  }
  async health() {
    const url = `${this.base}/api?module=account&action=txlist&address=0x0000000000000000000000000000000000000000&sort=desc&page=1&offset=1`;
    const data = await getJson(this.fetchFn, this.name, url);
    if (!data || (data.status === "0" && !Array.isArray(data.result))) {
      throw new ProviderError(this.name, "bad_response", "blockscout health check failed");
    }
    return this.name;
  }
}

/* ------------------------------------------------------------- SOL */

export class SolanaRPCFetcher {
  constructor(urls, fetchFn = fetch) {
    this.urls = urls; this.fetchFn = fetchFn; this.name = "solana-rpc"; this.last_errors = [];
  }
  async rpcOn(url, method, params) {
    const res = await this.fetchFn(url, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ jsonrpc: "2.0", id: 1, method, params }),
    });
    if (!res.ok) throw new ProviderError(url, kindForStatus(res.status), `RPC HTTP ${res.status}`, res.status);
    const data = await res.json();
    if (data.error) throw new ProviderError(url, "bad_response", `RPC error: ${JSON.stringify(data.error).slice(0, 200)}`);
    return data.result;
  }
  async rpc(method, params) {
    const errors = [];
    for (const url of this.urls) {
      try { return await this.rpcOn(url, method, params); }
      catch (e) { errors.push(e instanceof ProviderError ? e.asDict() : new ProviderError(url, "unreachable", String(e)).asDict()); }
    }
    throw new AllProvidersUnavailable(errors, "solana rpc");
  }
  async fetchAddress(address) {
    const sigs = await this.rpc("getSignaturesForAddress",
      [address, { limit: 50, commitment: "finalized" }]);
    if (!Array.isArray(sigs)) throw new ProviderError(this.name, "bad_response", "signatures not a list");
    const txs = [];
    for (const info of sigs) {
      if (!info || info.err || !info.signature) continue;
      const tx = await this.rpc("getTransaction",
        [info.signature, { encoding: "jsonParsed", commitment: "finalized", maxSupportedTransactionVersion: 0 }]);
      const normalized = normalizeSolTx(info, tx, address);
      if (normalized) txs.push(normalized);
    }
    return { txs, tip_height: null, provider: this.name, errors: [] };
  }
  async health() {
    await this.rpc("getSlot", [{ commitment: "finalized" }]);
    return this.name;
  }
}

export function normalizeSolTx(info, tx, receiveAddress) {
  if (!tx || !tx.meta || tx.meta.err) return null;
  const finalized = !info.confirmationStatus || info.confirmationStatus === "finalized";
  const keys = ((tx.transaction && tx.transaction.message && tx.transaction.message.accountKeys) || [])
    .map((k) => (typeof k === "string" ? k : k.pubkey));
  let amount = null, source = "";
  const instructions = ((tx.transaction && tx.transaction.message && tx.transaction.message.instructions) || []);
  for (const ix of instructions) {
    const parsed = ix.parsed;
    if (parsed && parsed.type === "transfer" && parsed.info
        && parsed.info.destination === receiveAddress) {
      amount = Number(parsed.info.lamports); source = parsed.info.source || "";
      break;
    }
  }
  if (amount === null) {
    const idx = keys.indexOf(receiveAddress);
    const pre = tx.meta.preBalances || [], post = tx.meta.postBalances || [];
    if (idx < 0 || idx >= pre.length || idx >= post.length) return null;
    amount = Number(post[idx]) - Number(pre[idx]);
    if (amount <= 0) return null;
    source = keys[0] || "";
  }
  if (!source) return null;
  return { txid: info.signature, from_addresses: [source], to_address: receiveAddress,
    value_amount: String(amount), confirmations: finalized ? 1 : 0, finalized };
}

export function buildChainFetcher(asset, fetchFn = fetch) {
  if (asset === "btc") return btcFetcher(fetchFn);
  if (asset === "eth") return new BlockscoutFetcher("https://eth.blockscout.com", "blockscout-eth", fetchFn);
  if (asset === "bnb") return new BlockscoutFetcher("https://bsc.blockscout.com", "blockscout-bnb", fetchFn);
  if (asset === "sol") return new SolanaRPCFetcher(
    ["https://api.mainnet-beta.solana.com", "https://solana-rpc.publicnode.com"], fetchFn);
  throw new Error(`no chain fetcher for ${asset}`);
}
