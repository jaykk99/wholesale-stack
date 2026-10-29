/* Order stores: MemoryStore for tests, D1Store for the Worker.
 * Same interface the paywatch Python stores expose: save, get,
 * allOpen, activeCounts, txidClaimedBy, counters, entitlements.
 */

const OPEN = ["pending", "confirming", "underpaid"];

export class MemoryStore {
  constructor() { this.orders = new Map(); this.counters = new Map(); this.entitlements = []; }
  async save(order) { this.orders.set(order.id, { ...order }); }
  async get(id) { const o = this.orders.get(id); return o ? { ...o } : null; }
  async allOpen() { return [...this.orders.values()].filter((o) => OPEN.includes(o.status)).map((o) => ({ ...o })); }
  async activeCounts(asset) {
    const counts = new Map();
    for (const o of this.orders.values()) {
      if (!OPEN.includes(o.status)) continue;
      if (asset && o.asset !== asset) continue;
      counts.set(o.receive_address, (counts.get(o.receive_address) || 0) + 1);
    }
    return counts;
  }
  async txidClaimedBy(txid, excludeId) {
    for (const o of this.orders.values()) {
      if (o.id !== excludeId && o.txid && o.txid === txid) return o.id;
    }
    return null;
  }
  async getCounter(name) { return Number(this.counters.get(name) || 0); }
  async setCounter(name, value) { this.counters.set(name, Number(value)); }
  async saveEntitlement(row) {
    this.entitlements = this.entitlements.filter((e) => e.order_id !== row.order_id);
    this.entitlements.push({ ...row });
  }
  async listEntitlements() { return [...this.entitlements].reverse(); }
}

const ORDER_COLUMNS = ["id", "plan_id", "price_usd", "payer_address",
  "receive_address", "expected_amount", "created_at", "status", "buyer_ref",
  "seen_amount", "seen_txid", "txid", "tx_received_amount", "confirmations",
  "paid_at", "expires_at", "late_payment_note", "asset",
  "required_confirmations", "provider", "provider_error", "last_checked_at"];

function rowToOrder(row) {
  if (!row) return null;
  return { ...row,
    price_usd: Number(row.price_usd),
    confirmations: Number(row.confirmations || 0),
    required_confirmations: Number(row.required_confirmations || 0) };
}

export class D1Store {
  constructor(db) { this.db = db; }
  async save(order) {
    const values = ORDER_COLUMNS.map((c) => order[c] === undefined ? null : order[c]);
    const placeholders = ORDER_COLUMNS.map(() => "?").join(",");
    await this.db.prepare(
      `INSERT OR REPLACE INTO orders (${ORDER_COLUMNS.join(",")}) VALUES (${placeholders})`)
      .bind(...values).run();
  }
  async get(id) {
    const row = await this.db.prepare("SELECT * FROM orders WHERE id = ?").bind(id).first();
    return rowToOrder(row);
  }
  async allOpen() {
    const res = await this.db.prepare(
      "SELECT * FROM orders WHERE status IN ('pending','confirming','underpaid')").all();
    return (res.results || []).map(rowToOrder);
  }
  async activeCounts(asset) {
    const res = await this.db.prepare(
      "SELECT receive_address, COUNT(*) AS n FROM orders WHERE asset = ? AND status IN ('pending','confirming','underpaid') GROUP BY receive_address")
      .bind(asset).all();
    const counts = new Map();
    for (const row of res.results || []) counts.set(row.receive_address, Number(row.n));
    return counts;
  }
  async txidClaimedBy(txid, excludeId) {
    const row = await this.db.prepare(
      "SELECT id FROM orders WHERE txid = ? AND id != ?").bind(txid, excludeId).first();
    return row ? row.id : null;
  }
  async getCounter(name) {
    const row = await this.db.prepare("SELECT value FROM meta WHERE key = ?").bind(name).first();
    return row ? Number(row.value) : 0;
  }
  async setCounter(name, value) {
    await this.db.prepare(
      "INSERT INTO meta (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value")
      .bind(name, Number(value)).run();
  }
  async saveEntitlement(row) {
    await this.db.prepare(
      "INSERT OR REPLACE INTO entitlements (order_id, plan_id, buyer_ref, asset, txid, granted_at) VALUES (?,?,?,?,?,?)")
      .bind(row.order_id, row.plan_id, row.buyer_ref || "", row.asset,
        row.txid || null, row.granted_at).run();
  }
  async listEntitlements() {
    const res = await this.db.prepare(
      "SELECT * FROM entitlements ORDER BY granted_at DESC").all();
    return res.results || [];
  }
}
