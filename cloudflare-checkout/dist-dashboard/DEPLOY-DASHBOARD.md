# Wholesale Stack crypto checkout - deploy via the Cloudflare dashboard (no wrangler)

Two files from this folder are all you need:

- `worker.js` (about 44 KB, single file, checkout page built in) - paste into the Worker editor
- `migration.sql` - paste into the D1 console

Order matters: database first, then the Worker, then the binding, then the cron trigger.

## 1. Create the D1 database

1. Cloudflare dashboard, pick the account (Jayomer1234@gmail.com's Account).
2. Left sidebar: **Storage & Databases** then **D1 SQL Database** then **Create**.
3. Name it exactly: `wholesale-checkout`
4. Click **Create**.

## 2. Run the schema

1. Click the new `wholesale-checkout` database to open it.
2. Open the **Console** tab.
3. Open `migration.sql` from this folder, copy ALL of it, paste it into the console, and run it (Execute).
4. It creates 3 tables: `orders`, `meta`, `entitlements`. No secrets go in the database.

## 3. Create the Worker and paste the code

1. Left sidebar: **Workers & Pages** then **Create** then **Worker** (the "Hello World" / start from scratch option).
2. Name it exactly: `wholesale-crypto-checkout`
3. Click **Deploy** (this deploys the placeholder code).
4. On the Worker's page, click **Edit code**.
5. Select all in the editor, delete, and paste the ENTIRE contents of `worker.js` from this folder.
6. Click **Deploy** (top right, "Save and Deploy" on some screens).

## 4. Add the D1 binding (name must be exactly DB)

1. Back on the Worker's page: **Settings** then **Bindings** then **Add**.
2. Choose **D1 database**.
3. Variable name: `DB` (exactly this, capital DB; the code reads `env.DB`)
4. Database: pick `wholesale-checkout`.
5. **Deploy** / save.

## 5. Add the cron trigger (the sweep)

1. Still in the Worker: **Settings** then **Triggers** then **Cron Triggers** then **Add**.
2. Schedule: `*/5 * * * *` (every 5 minutes). This sweeps open invoices and unlocks paid ones between buyer page checks.
3. Save.

## 6. Optional but recommended settings

Still in the Worker: **Settings** then **Variables and Secrets** then **Add**.

1. Real pricing (variable, plain text). Name `PAYWATCH_PLANS_JSON`.
   Value: your real plans JSON, for example
   `{"plans":[{"id":"access","name":"Access","price_usd":49,"duration_days":30}]}`
   Until this is set, the Worker serves the shipped PLACEHOLDER tiers and the checkout page shows a pricing-not-set warning and hides prices. Do not take payments until real pricing is set here and in the Python app's `paywatch_plans.json`.
2. Owner approval gate (type **Secret**, not plain text). Name `PAYWATCH_CRON_SECRET`.
   Value: any long random string you keep. When set, manual approval of an order requires that value; when unset, approvals are open, so set it before real use.

Receive addresses need no setup: the Worker's built-in default pools are the owner's public receive addresses (BTC, ETH, BNB, SOL). To override per asset, add a `PAYWATCH_ADDRESSES` variable with JSON pools.

## 7. Open it

URL format: `https://wholesale-crypto-checkout.<your-subdomain>.workers.dev`

The account's workers.dev subdomain is `jayomer1234`, so the expected URL is:

`https://wholesale-crypto-checkout.jayomer1234.workers.dev`

Workers do not sleep, so the checkout answers immediately at any hour.

## Quick checks if something is off

- Every API route says the D1 binding is not set (503): the binding in step 4 is missing or not named exactly `DB`, or the Worker was not redeployed after adding it.
- Orders never unlock on their own: the cron trigger in step 5 is missing, or buyers never press Check payment and the sweep is off. Add the trigger.
- One asset always says too busy (503 ASSET_UNAVAILABLE): that asset's price or chain providers are failing. Known case: BNB's public Blockscout explorer currently returns errors, so BNB stays unavailable until a working explorer exists. BTC, ETH, and SOL are the live assets.
- Page shows placeholder pricing: set `PAYWATCH_PLANS_JSON` per step 6 and redeploy.
