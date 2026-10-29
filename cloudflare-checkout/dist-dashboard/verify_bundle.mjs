/* Verify the dashboard-paste bundle offline: import dist-dashboard/worker.js
 * with a FakeD1 and drive its fetch handler. Live chain and price
 * providers are not called; only offline routes are exercised.
 * Run: node dist-dashboard/build.mjs && node dist-dashboard/verify_bundle.mjs
 */
import { FakeD1 } from "../tests/fake-d1.mjs";

const worker = (await import("./worker.js")).default;
let passed = 0, failed = 0;
function check(name, cond) {
  if (cond) { passed += 1; console.log(`ok - ${name}`); }
  else { failed += 1; console.log(`FAIL - ${name}`); }
}

const env = { DB: new FakeD1() };
let res = await worker.fetch(new Request("https://x/health"), env);
check("health 200", res.status === 200);

res = await worker.fetch(new Request("https://x/"), env);
const html = await res.text();
check("page 200 with placeholder warning", res.status === 200 && html.includes("Pricing is not set yet"));
check("page hides placeholder prices", !html.includes("$1.00"));

res = await worker.fetch(new Request("https://x/api/plans"), env);
const plans = await res.json();
check("plans endpoint flags placeholder pricing", plans.placeholder_pricing === true);
check("plans list has the placeholder tiers", plans.plans.length === 2
  && plans.plans.every((p) => p.id.startsWith("placeholder")));
check("asset pools present for btc eth bnb sol",
  plans.assets.length === 4 && plans.assets.every((a) => a.pool_size >= 1));

res = await worker.fetch(new Request("https://x/api/orders/nope"), env);
check("unknown order 404", res.status === 404);

res = await worker.fetch(new Request("https://x/api/orders", {
  method: "POST", headers: { "Content-Type": "application/json" }, body: "{}",
}), env);
check("create with missing fields 400", res.status === 400);

res = await worker.fetch(new Request("https://x/api/entitlements"), env);
const ents = await res.json();
check("entitlements endpoint answers with an empty list",
  Array.isArray(ents.entitlements) && ents.entitlements.length === 0);

console.log(`\nbundle checks: ${passed} passed, ${failed} failed`);
process.exit(failed ? 1 : 0);
