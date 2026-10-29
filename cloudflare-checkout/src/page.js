/* Checkout page, served by the Worker itself so the dashboard paste
 * bundle needs no ASSETS binding. Prices render only when the plans
 * are not placeholders; placeholder mode shows a pricing-not-set
 * warning and never invents a price. */
export function checkoutPage({ plans, assets, placeholder }) {
  const planOptions = plans.map((p) =>
    `<option value="${p.id}">${escapeHtml(p.name)}</option>`).join("");
  const planCards = plans.map((p) => `
    <div class="card"><strong>${escapeHtml(p.name)}</strong><br>
    ${placeholder
      ? "<span>Price: not set yet (placeholder plan)</span>"
      : `<span>Price: $${Number(p.price_usd).toFixed(2)} USD, pinned in crypto at checkout</span>`}
    </div>`).join("");
  const assetOptions = assets.map((a) =>
    `<option value="${a.key}">${a.symbol}</option>`).join("");
  const assetList = assets.map((a) => `
    <li>${a.symbol} (${escapeHtml(a.name)}): ${a.confirmations} confirmation rule,
    pool of ${a.pool_size} receive address${a.pool_size === 1 ? "" : "es"}
    ${a.pool_size === 0 ? " - checkout closed for this asset" : ""}</li>`).join("");
  return `<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Crypto Checkout - Wholesale Stack</title>
<style>
body{font-family:system-ui,sans-serif;max-width:720px;margin:24px auto;padding:0 16px;background:#0b0e12;color:#e8ecf1}
.card{border:1px solid #3a4350;border-radius:8px;padding:12px;margin:8px 0}
.warn{border:2px solid #c0392b;border-radius:8px;padding:12px;margin:12px 0}
input,select,button{font-size:16px;padding:8px;margin:4px 0}
button{background:#2d7dd2;color:#fff;border:0;border-radius:6px;cursor:pointer}
pre{white-space:pre-wrap;word-break:break-all;background:#12161c;padding:12px;border-radius:8px}
a{color:#7ab3f5}
</style></head><body>
<h1>Crypto checkout</h1>
<p>Pay in crypto from your own wallet. No wallet connection, no signing,
no card. You declare the address you will send from, pay the pinned
amount to the receive address shown, and the plan unlocks after the
asset confirmation rule inside a 60 minute window. At least 99 percent
of the pinned amount must arrive, from the address you declared.
Late, underpaid, or reused payments do not auto unlock.</p>
${placeholder ? `<div class="warn"><strong>Pricing is not set yet.</strong>
The plans below are placeholders. The owner must set real names and
prices (PAYWATCH_PLANS_JSON on this Worker) before anyone pays.
Do not send crypto for a placeholder plan.</div>` : ""}
<h2>Plans</h2>${planCards}
<h2>Assets</h2><ul>${assetList}</ul>
<p>BNB note: the public BNB explorer currently fails, so BNB checkouts
refuse honestly with a too busy message until a working explorer is
configured. BTC, ETH, and SOL are the live assets.</p>
<h2>Start a payment</h2>
<form id="payForm">
<label>Plan<br><select id="plan_id">${planOptions}</select></label><br>
<label>Asset<br><select id="asset">${assetOptions}</select></label><br>
<label>Your sending address (you must send from exactly this address)<br>
<input id="payer_address" size="48" required></label><br>
<label>Reference (optional)<br><input id="buyer_ref" size="24"></label><br>
<button type="submit">Create invoice</button>
</form>
<pre id="out"></pre>
<button id="checkBtn" style="display:none">Check payment</button>
<p><a href="/api/plans">API: plans</a> - <a href="/api/assets">API: asset status</a></p>
<script>
let currentOrder = null;
const out = document.getElementById('out');
document.getElementById('payForm').addEventListener('submit', async (e) => {
  e.preventDefault();
  out.textContent = 'Creating invoice...';
  const res = await fetch('/api/orders', { method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({
      plan_id: document.getElementById('plan_id').value,
      asset: document.getElementById('asset').value,
      payer_address: document.getElementById('payer_address').value,
      buyer_ref: document.getElementById('buyer_ref').value })});
  const data = await res.json();
  if (!res.ok) { out.textContent = 'Error: ' + (data.error || res.status); return; }
  currentOrder = data;
  out.textContent = 'Send exactly this amount to the receive address:\\n' +
    'Amount (smallest unit): ' + data.expected_amount + '\\n' +
    'Receive address: ' + data.receive_address + '\\n' +
    'Expires at: ' + data.expires_at + '\\nStatus: ' + data.status;
  document.getElementById('checkBtn').style.display = 'inline';
});
document.getElementById('checkBtn').addEventListener('click', async () => {
  if (!currentOrder) return;
  const res = await fetch('/api/orders/' + currentOrder.id + '/check', { method: 'POST' });
  out.textContent = JSON.stringify(await res.json(), null, 2);
});
</script>
</body></html>`;
}

function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, (c) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  }[c]));
}
