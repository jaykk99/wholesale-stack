# Wholesale Stack crypto checkout - Cloudflare Worker

A standalone JavaScript port of the crypto payment watcher
(jaykk99/crypto-payment-watcher) for Wholesale Stack. The main app is
Python FastAPI and cannot run on Cloudflare free, so the checkout
itself lives here as a Worker: no sleeping, D1 invoice state, and a
cron-trigger sweep every 5 minutes.

Same rules as the Python watcher:

- Price pinned at invoice creation (CoinGecko, then Coinbase, then
  Kraken; brief stale-cache fallback, marked stale)
- Buyer declares their sending address first (payer binding)
- 60 minute invoice window; a qualifying payment after expiry is
  recorded as paid_late and never auto unlocks
- 1 percent tolerance (at least 99 percent of the pinned amount)
- Confirmations: BTC 2, ETH 12, BNB 15, SOL finalized
- Single-use transaction id across all orders
- Per-asset busy state: when an asset's price or chain providers are
  down, creating an invoice for that asset returns 503
  ASSET_UNAVAILABLE with a pick-another-crypto message, and the other
  assets keep selling
- Owner manual approve as the fallback, gated by PAYWATCH_CRON_SECRET
  when that secret is set

Chain providers: BTC mempool.space then blockstream.info, ETH and BNB
Blockscout, SOL the public Solana RPCs (mainnet-beta, then publicnode).
Known limit: the public BNB Blockscout explorer currently returns
errors, so BNB fails closed as unavailable until a working explorer is
configured. BTC, ETH, and SOL verified live on the Python side.

Receive addresses: built-in default pools are the owner's public
receive addresses (same defaults the paywatch package ships). PAYWATCH_ADDRESSES
or per-asset PAYWATCH_<ASSET>_ADDRESSES variables override per asset;
an explicitly empty pool closes that asset.

Plans: PAYWATCH_PLANS_JSON on the Worker, otherwise the shipped
PLACEHOLDER tiers (price 1, names marked PLACEHOLDER). The checkout
page hides prices and warns while placeholder pricing is active.
Wholesale Stack has no real crypto pricing yet; set real plans before
selling.

Paid means: an entitlement row in the D1 `entitlements` table (and, in
the Python app, a `crypto_entitlements` row plus a lead note). That row
is the paid flag staff check.

## Layout

- `src/core.js` asset registry, default pools, validators, amount math, matcher
- `src/providers.js` price and chain providers with failover
- `src/service.js` order flow (create, check, sweep, approve)
- `src/store.js` MemoryStore (tests) and D1Store
- `src/page.js` the checkout page (served by the Worker, no assets binding)
- `src/worker.js` routes plus the scheduled sweep handler
- `migrations/0001_init.sql` D1 schema
- `tests/` offline tests with mocked providers (`npm test`)
- `dist-dashboard/` single-file bundle plus deploy notes for the
  Cloudflare dashboard paste flow (`npm run build-bundle`, then
  `npm run verify-bundle`)

## Local checks

```bash
npm test
npm run build-bundle
npm run verify-bundle
```

Deploy: follow `dist-dashboard/DEPLOY-DASHBOARD.md` (dashboard paste,
no wrangler needed), or use `wrangler.toml` with wrangler if available.
