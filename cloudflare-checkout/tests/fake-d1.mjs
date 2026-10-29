/* Minimal in-memory D1 stand-in covering exactly the statements
 * D1Store issues. Used by the test suite and the bundle verifier so
 * the D1 code path is exercised offline, not just the memory store. */
export class FakeD1 {
  constructor() {
    this.orders = new Map(); this.meta = new Map(); this.entitlements = new Map();
  }
  prepare(sql) {
    const db = this;
    let binds = [];
    const stmt = {
      bind(...values) { binds = values; return stmt; },
      async run() { db.exec(sql, binds); return { success: true }; },
      async first() { const rows = db.query(sql, binds); return rows[0] || null; },
      async all() { return { results: db.query(sql, binds) }; },
    };
    return stmt;
  }
  exec(sql, b) {
    let m;
    if ((m = sql.match(/INSERT OR REPLACE INTO orders \(([^)]+)\)/))) {
      const cols = m[1].split(",").map((s) => s.trim());
      const row = {};
      cols.forEach((c, i) => { row[c] = b[i]; });
      this.orders.set(row.id, row);
      return;
    }
    if (sql.startsWith("INSERT INTO meta")) { this.meta.set(b[0], b[1]); return; }
    if ((m = sql.match(/INSERT OR REPLACE INTO entitlements \(([^)]+)\)/))) {
      const cols = m[1].split(",").map((s) => s.trim());
      const row = {};
      cols.forEach((c, i) => { row[c] = b[i]; });
      this.entitlements.set(row.order_id, row);
      return;
    }
    throw new Error(`FakeD1 exec does not handle: ${sql}`);
  }
  query(sql, b) {
    if (sql.includes("FROM orders WHERE id = ?")) {
      const row = this.orders.get(b[0]);
      return row ? [{ ...row }] : [];
    }
    if (sql.includes("COUNT(*) AS n")) {
      const counts = new Map();
      for (const o of this.orders.values()) {
        if (o.asset === b[0] && ["pending", "confirming", "underpaid"].includes(o.status)) {
          counts.set(o.receive_address, (counts.get(o.receive_address) || 0) + 1);
        }
      }
      return [...counts.entries()].map(([receive_address, n]) => ({ receive_address, n }));
    }
    if (sql.includes("FROM orders WHERE status IN")) {
      return [...this.orders.values()]
        .filter((o) => ["pending", "confirming", "underpaid"].includes(o.status))
        .map((o) => ({ ...o }));
    }
    if (sql.includes("FROM orders WHERE txid = ?")) {
      return [...this.orders.values()]
        .filter((o) => o.txid === b[0] && o.id !== b[1])
        .map((o) => ({ id: o.id }));
    }
    if (sql.includes("FROM meta WHERE key = ?")) {
      return this.meta.has(b[0]) ? [{ value: this.meta.get(b[0]) }] : [];
    }
    if (sql.includes("FROM entitlements")) {
      return [...this.entitlements.values()]
        .sort((x, y) => y.granted_at - x.granted_at).map((o) => ({ ...o }));
    }
    throw new Error(`FakeD1 query does not handle: ${sql}`);
  }
}
