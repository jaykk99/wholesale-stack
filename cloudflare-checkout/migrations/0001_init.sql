-- Wholesale Stack crypto checkout - D1 schema.
-- Amounts are stored as TEXT: wei and lamport values exceed the exact
-- integer range of JS numbers, so smallest units stay decimal strings.
CREATE TABLE IF NOT EXISTS orders (
  id TEXT PRIMARY KEY,
  plan_id TEXT,
  price_usd REAL,
  payer_address TEXT,
  receive_address TEXT,
  expected_amount TEXT,
  created_at TEXT,
  status TEXT,
  buyer_ref TEXT DEFAULT '',
  seen_amount TEXT DEFAULT '0',
  seen_txid TEXT,
  txid TEXT,
  tx_received_amount TEXT DEFAULT '0',
  confirmations INTEGER DEFAULT 0,
  paid_at TEXT,
  expires_at TEXT,
  late_payment_note TEXT,
  asset TEXT DEFAULT 'btc',
  required_confirmations INTEGER DEFAULT 2,
  provider TEXT,
  provider_error TEXT,
  last_checked_at TEXT
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_orders_txid ON orders(txid) WHERE txid IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_orders_asset_receive_status ON orders(asset, receive_address, status);
CREATE TABLE IF NOT EXISTS meta (
  key TEXT PRIMARY KEY,
  value INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS entitlements (
  order_id TEXT PRIMARY KEY,
  plan_id TEXT NOT NULL,
  buyer_ref TEXT DEFAULT '',
  asset TEXT DEFAULT 'btc',
  txid TEXT,
  granted_at INTEGER NOT NULL
);
