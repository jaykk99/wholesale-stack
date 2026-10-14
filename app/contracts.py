"""Wholesaling contract templates: fillable, auto-filled from the deal, printable.

Standard disclaimer: these are common wholesaling templates, not legal advice.
Have a local lawyer review before use.
"""
import os
from string import Template

BUYER_NAME = os.environ.get("WHOLESALE_BUYER_NAME", "")
BUYER_COMPANY = os.environ.get("WHOLESALE_BUYER_COMPANY", "")

PURCHASE_AGREEMENT = Template("""<h2>Residential Purchase Agreement</h2>
<p class="muted">This agreement is made on <strong>$date</strong>, between:</p>
<p><strong>Seller:</strong> $seller_name ($seller_phone)<br>
<strong>Buyer:</strong> $buyer_name</p>
<p><strong>Property:</strong> $property_address, $city $postal</p>
<ol>
<li><strong>Purchase price.</strong> Buyer agrees to purchase the Property for <strong>$$$purchase_price</strong> (the "Purchase Price").</li>
<li><strong>Earnest money.</strong> Buyer deposits <strong>$$$earnest_amount</strong> as earnest money with $escrow_holder within 3 business days of acceptance. The deposit applies to the Purchase Price at closing.</li>
<li><strong>As-is sale.</strong> Buyer accepts the Property in its present as-is condition. Seller makes no warranties as to condition except clear title.</li>
<li><strong>Closing.</strong> Closing shall occur on or before <strong>$closing_date</strong> at a title company or lawyer's office chosen by Buyer, unless extended in writing.</li>
<li><strong>Title.</strong> Seller shall convey marketable title free of liens and encumbrances except those of record accepted by Buyer.</li>
<li><strong>Inspection period.</strong> Buyer has $inspection_days days from acceptance to inspect and may cancel in writing for any reason, with earnest money refunded.</li>
<li><strong>Assignment.</strong> Buyer may assign this agreement in whole or in part without Seller's consent.</li>
<li><strong>Closing costs.</strong> Each party pays its own closing costs unless agreed otherwise in writing.</li>
<li><strong>Entire agreement.</strong> This is the entire agreement between the parties regarding the Property.</li>
</ol>
<div class="siggrid">
<div><p>Seller: $seller_name</p><p class="sigline">Signature / Date</p></div>
<div><p>Buyer: $buyer_name</p><p class="sigline">Signature / Date</p></div>
</div>""")

ASSIGNMENT = Template("""<h2>Assignment of Real Estate Purchase Agreement</h2>
<p class="muted">Dated <strong>$date</strong></p>
<p><strong>Assignor (Wholesaler):</strong> $buyer_name<br>
<strong>Assignee (End Buyer):</strong> $assignee_name<br>
<strong>Property:</strong> $property_address, $city $postal</p>
<ol>
<li><strong>Assignment.</strong> Assignor assigns to Assignee all of Assignor's right, title, and interest in the purchase agreement dated $original_agreement_date between Assignor and $seller_name for the Property (the "Original Agreement").</li>
<li><strong>Assignment fee.</strong> Assignee pays Assignor a non-refundable assignment fee of <strong>$$$assignment_fee</strong>, due at closing and disbursed from closing proceeds.</li>
<li><strong>Assumption.</strong> Assignee assumes all of Assignor's obligations under the Original Agreement from the date of closing.</li>
<li><strong>Original terms control.</strong> The purchase price of <strong>$$$purchase_price</strong> and all other terms of the Original Agreement remain unchanged.</li>
<li><strong>Release.</strong> Upon closing, Assignor is released from further obligation under the Original Agreement.</li>
</ol>
<div class="siggrid">
<div><p>Assignor: $buyer_name</p><p class="sigline">Signature / Date</p></div>
<div><p>Assignee: $assignee_name</p><p class="sigline">Signature / Date</p></div>
</div>""")

EARNEST_RECEIPT = Template("""<h2>Earnest Money Deposit Receipt</h2>
<p class="muted">Dated <strong>$date</strong></p>
<p>Received from <strong>$buyer_name</strong> the sum of <strong>$$$earnest_amount</strong>
as earnest money toward the purchase of <strong>$property_address, $city $postal</strong>,
per the purchase agreement dated $original_agreement_date.</p>
<p>Funds held by: <strong>$escrow_holder</strong></p>
<div class="siggrid">
<div><p>Received by:</p><p class="sigline">Signature / Date</p></div>
<div><p>Buyer: $buyer_name</p><p class="sigline">Signature / Date</p></div>
</div>""")

TEMPLATES = [
    {
        "id": "purchase_agreement",
        "title": "Purchase Agreement",
        "description": "Cash offer contract between you and the seller. As-is, assignable.",
        "template": PURCHASE_AGREEMENT,
        "fields": [
            {"name": "seller_name", "label": "Seller name", "from": "owner_name"},
            {"name": "seller_phone", "label": "Seller phone", "from": "owner_phone"},
            {"name": "property_address", "label": "Property address", "from": "address"},
            {"name": "city", "label": "City", "from": "city"},
            {"name": "postal", "label": "Postal / ZIP", "from": "postal"},
            {"name": "buyer_name", "label": "Buyer name", "from": "buyer_default"},
            {"name": "purchase_price", "label": "Purchase price", "from": "offer_amount"},
            {"name": "earnest_amount", "label": "Earnest money", "default": "500"},
            {"name": "escrow_holder", "label": "Escrow / title holder", "default": ""},
            {"name": "closing_date", "label": "Closing date", "default": ""},
            {"name": "inspection_days", "label": "Inspection days", "default": "10"},
            {"name": "date", "label": "Agreement date", "from": "today"},
        ],
    },
    {
        "id": "assignment",
        "title": "Assignment of Contract",
        "description": "Sell your position in the deal to an end buyer for a fee.",
        "template": ASSIGNMENT,
        "fields": [
            {"name": "seller_name", "label": "Original seller", "from": "owner_name"},
            {"name": "property_address", "label": "Property address", "from": "address"},
            {"name": "city", "label": "City", "from": "city"},
            {"name": "postal", "label": "Postal / ZIP", "from": "postal"},
            {"name": "buyer_name", "label": "Assignor (you)", "from": "buyer_default"},
            {"name": "assignee_name", "label": "Assignee (end buyer)", "default": ""},
            {"name": "purchase_price", "label": "Original purchase price", "from": "offer_amount"},
            {"name": "assignment_fee", "label": "Your assignment fee", "default": ""},
            {"name": "original_agreement_date", "label": "Original agreement date", "default": ""},
            {"name": "date", "label": "Assignment date", "from": "today"},
        ],
    },
    {
        "id": "earnest_receipt",
        "title": "Earnest Money Receipt",
        "description": "Paper trail for the deposit handed over with the offer.",
        "template": EARNEST_RECEIPT,
        "fields": [
            {"name": "buyer_name", "label": "Buyer name", "from": "buyer_default"},
            {"name": "property_address", "label": "Property address", "from": "address"},
            {"name": "city", "label": "City", "from": "city"},
            {"name": "postal", "label": "Postal / ZIP", "from": "postal"},
            {"name": "earnest_amount", "label": "Earnest amount", "default": "500"},
            {"name": "escrow_holder", "label": "Held by", "default": ""},
            {"name": "original_agreement_date", "label": "Purchase agreement date", "default": ""},
            {"name": "date", "label": "Receipt date", "from": "today"},
        ],
    },
]


def get_template(tid: str) -> dict | None:
    return next((t for t in TEMPLATES if t["id"] == tid), None)


def autofill_values(template: dict, lead: dict) -> dict:
    """Pre-fill field values from the lead / owner / deal record."""
    import datetime
    owner = (lead.get("owners") or [{}])[0]
    mapping = {
        "owner_name": owner.get("name", ""),
        "owner_phone": owner.get("phone", ""),
        "address": lead.get("address", ""),
        "city": lead.get("city", ""),
        "postal": lead.get("postal", ""),
        "offer_amount": str(lead.get("offer_amount") or lead.get("asking_price") or ""),
        "buyer_default": BUYER_COMPANY or BUYER_NAME,
        "today": datetime.date.today().isoformat(),
    }
    values = {}
    for f in template["fields"]:
        if f.get("from"):
            values[f["name"]] = mapping.get(f["from"], "")
        else:
            values[f["name"]] = f.get("default", "")
    return values


def render_contract(template: dict, values: dict) -> str:
    safe = {f["name"]: values.get(f["name"], "") for f in template["fields"]}
    return template["template"].safe_substitute(safe)
