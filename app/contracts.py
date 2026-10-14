"""Wholesaling contract template library: fillable, auto-filled from the deal, printable.

Template only, not legal advice. Have a local real estate attorney review
every document before use.
"""
import os
from string import Template

BUYER_NAME = os.environ.get("WHOLESALE_BUYER_NAME", "")
BUYER_COMPANY = os.environ.get("WHOLESALE_BUYER_COMPANY", "")

DISCLAIMER_HTML = """
<div class="disclaimer">
<p><strong>Disclaimer.</strong> This is a template only, not legal advice.
Have a local real estate attorney review this document before use. Laws vary
by province and state.</p>
</div>"""

CATEGORIES = [
    "Core Deal Documents",
    "Pre-Contract",
    "Deal Protection",
    "Partnerships",
    "Pre-Foreclosure",
    "Credibility",
    "Exit",
]

# ---------------------------------------------------------------------------
# 1. Wholesale Purchase Agreement
# ---------------------------------------------------------------------------
PURCHASE_AGREEMENT = Template("""<h2>Residential Purchase Agreement</h2>
<p class="muted">This agreement is made on <strong>$date</strong>, between:</p>
<p><strong>Seller:</strong> $seller_name ($seller_phone)<br>
<strong>Buyer:</strong> $buyer_name<br>
<strong>Property:</strong> $property_address, $city $postal</p>

<ol>
<li><strong>Purchase price.</strong> Buyer agrees to purchase the Property for <strong>$$$purchase_price</strong> (the "Purchase Price").</li>

<li><strong>Earnest money.</strong> Buyer deposits <strong>$$$earnest_amount</strong> as earnest money with $escrow_holder within $earnest_days business days of acceptance. The deposit is applied to the Purchase Price at closing. If Buyer cancels during the inspection period, the deposit is refunded in full.</li>

<li><strong>Inspection period.</strong> Buyer has <strong>$inspection_days days</strong> from acceptance (the "Inspection Period") to inspect the Property, review title, and conduct any due diligence. Buyer may cancel this agreement in writing for any reason during the Inspection Period, with the earnest money refunded in full.</li>

<li><strong>As-is sale.</strong> Except as stated in the seller disclosures below, Buyer accepts the Property in its present as-is condition. Seller makes no warranties as to the physical condition of the Property.</li>

<li><strong>Seller disclosures.</strong> To Seller's knowledge, the Property: (a) has no undisclosed structural defects, (b) has no unpermitted additions, (c) is not subject to any pending legal action or government notice except as disclosed here: $disclosures.</li>

<li><strong>Title.</strong> Seller shall convey marketable title free of liens and encumbrances except those of record accepted by Buyer. Seller will clear all liens, judgments, and back taxes before or at closing unless otherwise agreed in writing.</li>

<li><strong>Closing.</strong> Closing shall occur on or before <strong>$closing_date</strong> at a title company, notary, or lawyer's office chosen by Buyer, unless extended by mutual written agreement.</li>

<li><strong>Assignment.</strong> Buyer may assign this agreement, in whole or in part, without Seller's consent. Any assignee assumes Buyer's obligations under this agreement.</li>

<li><strong>Closing costs.</strong> Each party pays its own closing costs unless agreed otherwise in writing.</li>

<li><strong>Personal property.</strong> The following personal property is included in the sale: $personal_property.</li>

<li><strong>Default.</strong> If Seller defaults, Buyer may seek specific performance or cancel and recover the earnest money. If Buyer defaults after the Inspection Period, Seller's sole remedy is retention of the earnest money.</li>

<li><strong>Entire agreement.</strong> This is the entire agreement between the parties regarding the Property. Changes must be in writing and signed by both parties.</li>
</ol>

<div class="siggrid">
<div><p><strong>Seller:</strong> $seller_name</p><p class="sigline">Signature / Date</p></div>
<div><p><strong>Buyer:</strong> $buyer_name</p><p class="sigline">Signature / Date</p></div>
</div>""")

# ---------------------------------------------------------------------------
# 2. Assignment of Contract
# ---------------------------------------------------------------------------
ASSIGNMENT = Template("""<h2>Assignment of Real Estate Purchase Agreement</h2>
<p class="muted">Dated <strong>$date</strong></p>
<p><strong>Assignor (Wholesaler):</strong> $buyer_name<br>
<strong>Assignee (End Buyer):</strong> $assignee_name<br>
<strong>Property:</strong> $property_address, $city $postal</p>

<ol>
<li><strong>Assignment.</strong> Assignor assigns to Assignee all of Assignor's right, title, and interest in the purchase agreement dated $original_agreement_date between Assignor and $seller_name for the Property (the "Original Agreement").</li>

<li><strong>Assignment fee.</strong> Assignee pays Assignor a non-refundable assignment fee of <strong>$$$assignment_fee</strong>. The fee is due at closing and shall be disbursed to Assignor from the closing proceeds. If the transaction does not close for any reason other than Assignor's default, the fee is not owed.</li>

<li><strong>Assumption.</strong> Assignee assumes all of Assignor's obligations under the Original Agreement from the date of closing.</li>

<li><strong>Original terms control.</strong> The purchase price of <strong>$$$purchase_price</strong> and all other terms of the Original Agreement remain unchanged. Assignee has reviewed the Original Agreement and accepts its terms.</li>

<li><strong>Inspection.</strong> Assignee acknowledges any inspection period under the Original Agreement. Assignee has had the opportunity to inspect the Property.</li>

<li><strong>Release.</strong> Upon closing, Assignor is released from further obligation under the Original Agreement.</li>

<li><strong>No broker relationship.</strong> The parties acknowledge Assignor is acting as a principal, not as a licensed real estate agent or broker, unless separately disclosed.</li>
</ol>

<div class="siggrid">
<div><p><strong>Assignor:</strong> $buyer_name</p><p class="sigline">Signature / Date</p></div>
<div><p><strong>Assignee:</strong> $assignee_name</p><p class="sigline">Signature / Date</p></div>
</div>""")

# ---------------------------------------------------------------------------
# 3. Earnest Money Receipt
# ---------------------------------------------------------------------------
EARNEST_RECEIPT = Template("""<h2>Earnest Money Deposit Receipt</h2>
<p class="muted">Dated <strong>$date</strong></p>
<p>Received from <strong>$buyer_name</strong> the sum of <strong>$$$earnest_amount</strong>
($earnest_amount_words) as earnest money toward the purchase of
<strong>$property_address, $city $postal</strong>, per the purchase agreement
dated $original_agreement_date.</p>

<p><strong>Funds held by:</strong> $escrow_holder<br>
<strong>Terms:</strong> Funds will be applied to the purchase price at closing. If the buyer cancels within the inspection period stated in the purchase agreement, funds will be refunded in full within 5 business days.</p>

<div class="siggrid">
<div><p><strong>Received by:</strong></p><p class="sigline">Signature / Date</p></div>
<div><p><strong>Buyer:</strong> $buyer_name</p><p class="sigline">Signature / Date</p></div>
</div>""")

# ---------------------------------------------------------------------------
# 4. Letter of Intent (LOI)
# ---------------------------------------------------------------------------
LETTER_OF_INTENT = Template("""<h2>Letter of Intent to Purchase Real Property</h2>
<p class="muted">Dated <strong>$date</strong> &mdash; <strong>Non-binding</strong></p>

<p><strong>To:</strong> $seller_name<br>
<strong>Re:</strong> $property_address, $city $postal (the "Property")</p>

<p>Dear $seller_name,</p>

<p>This letter states our intent to negotiate a purchase of the Property on the
following proposed terms. This letter is <strong>not a binding agreement</strong>;
a binding agreement will exist only if both parties sign a formal purchase agreement.</p>

<ol>
<li><strong>Proposed purchase price:</strong> <strong>$$$purchase_price</strong></li>
<li><strong>Earnest money:</strong> $$$earnest_amount, refundable during inspection</li>
<li><strong>Inspection period:</strong> $inspection_days days from signed agreement</li>
<li><strong>Target closing date:</strong> $closing_date</li>
<li><strong>Conditions:</strong> as-is sale; buyer may assign the contract; marketable title required</li>
</ol>

<p>If these terms are acceptable in principle, please sign below and we will
prepare the formal purchase agreement within $agreement_days business days.</p>

<div class="siggrid">
<div><p><strong>Buyer:</strong> $buyer_name</p><p class="sigline">Signature / Date</p></div>
<div><p><strong>Seller (acknowledging intent only):</strong> $seller_name</p><p class="sigline">Signature / Date</p></div>
</div>""")

# ---------------------------------------------------------------------------
# 5. Option Agreement
# ---------------------------------------------------------------------------
OPTION_AGREEMENT = Template("""<h2>Option to Purchase Real Property</h2>
<p class="muted">Dated <strong>$date</strong></p>
<p><strong>Optionor (Seller):</strong> $seller_name<br>
<strong>Optionee (Buyer):</strong> $buyer_name<br>
<strong>Property:</strong> $property_address, $city $postal</p>

<ol>
<li><strong>Grant of option.</strong> In exchange for the option fee below, Optionor grants Optionee the <strong>exclusive</strong> right to purchase the Property on the terms in this agreement.</li>

<li><strong>Option fee.</strong> Optionee pays Optionor a non-refundable option fee of <strong>$$$option_fee</strong> upon signing. The option fee is credited toward the purchase price if Optionee exercises the option.</li>

<li><strong>Option period.</strong> This option is valid for <strong>$option_days days</strong> from the date above (the "Option Period"). Optionee may exercise the option at any time during the Option Period by delivering written notice to Optionor.</li>

<li><strong>Exercise.</strong> Upon exercise, the parties will close on the terms below within $closing_days days of the exercise notice.</li>

<li><strong>Purchase price.</strong> <strong>$$$purchase_price</strong>, less the option fee already paid.</li>

<li><strong>Exclusivity.</strong> During the Option Period, Optionor will not sell, list, or encumber the Property, nor negotiate with other buyers.</li>

<li><strong>Inspection.</strong> Optionee may inspect the Property at reasonable times during the Option Period.</li>

<li><strong>Expiration.</strong> If Optionee does not exercise the option before the Option Period ends, this agreement terminates and Optionor keeps the option fee.</li>

<li><strong>Assignment.</strong> Optionee may assign this option without Optionor's consent.</li>
</ol>

<div class="siggrid">
<div><p><strong>Optionor:</strong> $seller_name</p><p class="sigline">Signature / Date</p></div>
<div><p><strong>Optionee:</strong> $buyer_name</p><p class="sigline">Signature / Date</p></div>
</div>""")

# ---------------------------------------------------------------------------
# 6. Memorandum of Agreement
# ---------------------------------------------------------------------------
MEMORANDUM_OF_AGREEMENT = Template("""<h2>Memorandum of Agreement</h2>
<p class="muted"><strong>For recording</strong> &mdash; gives public notice of the purchase agreement</p>

<p><strong>Seller:</strong> $seller_name<br>
<strong>Buyer:</strong> $buyer_name<br>
<strong>Property:</strong> $property_address, $city $postal<br>
<strong>Legal description:</strong> $legal_description</p>

<p>Notice is hereby given that on <strong>$original_agreement_date</strong>, Seller
and Buyer entered into a purchase agreement for the Property described above
(the "Agreement"). This memorandum is recorded to give public notice of Buyer's
equitable interest in the Property under the Agreement.</p>

<p>This memorandum does not modify the Agreement. It is recorded solely to
protect Buyer's interest and to provide notice to third parties, including
title companies and subsequent purchasers, that the Property is under contract.</p>

<div class="siggrid">
<div><p><strong>Seller:</strong> $seller_name</p><p class="sigline">Signature / Date</p></div>
<div><p><strong>Buyer:</strong> $buyer_name</p><p class="sigline">Signature / Date</p></div>
</div>

<p class="muted"><strong>Notary acknowledgement:</strong></p>
<p class="muted">State/Province of ___________, County of ___________. Before me on $date
personally appeared $seller_name and $buyer_name, known to me to be the persons
who signed above, and acknowledged the signing as their free act.</p>
<p class="sigline">Notary signature / seal / commission expiry</p>""")

# ---------------------------------------------------------------------------
# 7. Joint Venture Agreement
# ---------------------------------------------------------------------------
JOINT_VENTURE = Template("""<h2>Joint Venture Agreement &mdash; Real Estate Wholesale Deal</h2>
<p class="muted">Dated <strong>$date</strong></p>
<p><strong>Partner A:</strong> $partner_a_name<br>
<strong>Partner B:</strong> $partner_b_name<br>
<strong>Property:</strong> $property_address, $city $postal</p>

<ol>
<li><strong>Purpose.</strong> The partners form this joint venture solely to acquire and assign (or otherwise dispose of) the purchase contract for the Property described above (the "Deal").</li>

<li><strong>Roles.</strong><br>
Partner A responsibilities: $partner_a_role<br>
Partner B responsibilities: $partner_b_role</li>

<li><strong>Capital contributions.</strong> Partner A contributes: $partner_a_contribution. Partner B contributes: $partner_b_contribution. Earnest money and marketing costs are split as agreed here.</li>

<li><strong>Profit split.</strong> Net profits from the Deal (assignment fee or spread, minus shared costs) are split: <strong>Partner A: $partner_a_split% / Partner B: $partner_b_split%</strong>.</li>

<li><strong>Decision making.</strong> Offers, price changes, and contract cancellations require written agreement of both partners.</li>

<li><strong>Expenses.</strong> Shared deal expenses are reimbursed from proceeds before profit is split. Each partner keeps receipts.</li>

<li><strong>Term.</strong> This venture ends when the Deal closes, is cancelled, or on $end_date, whichever comes first.</li>

<li><strong>Confidentiality.</strong> Partners will not disclose the other partner's buyers, sellers, or deal terms to third parties without written consent.</li>

<li><strong>Non-circumvention.</strong> For 12 months after this agreement ends, neither partner will bypass the other to do a deal with a party introduced through this venture.</li>

<li><strong>Disputes.</strong> The partners will attempt mediation before any legal action.</li>
</ol>

<div class="siggrid">
<div><p><strong>Partner A:</strong> $partner_a_name</p><p class="sigline">Signature / Date</p></div>
<div><p><strong>Partner B:</strong> $partner_b_name</p><p class="sigline">Signature / Date</p></div>
</div>""")

# ---------------------------------------------------------------------------
# 8. Authorization to Release Information
# ---------------------------------------------------------------------------
AUTHORIZATION_RELEASE = Template("""<h2>Authorization to Release Information</h2>
<p class="muted">Dated <strong>$date</strong></p>

<p><strong>Borrower (Seller):</strong> $seller_name<br>
<strong>Property:</strong> $property_address, $city $postal<br>
<strong>Lender / Servicer:</strong> $lender_name<br>
<strong>Loan number:</strong> $loan_number</p>

<p>I, <strong>$seller_name</strong>, authorize <strong>$buyer_name</strong> (and their
representatives) to communicate with my lender/servicer named above regarding
my mortgage loan, including: loan balance, payoff amount, reinstatement amount,
foreclosure status and sale date, loss mitigation and short sale options, and
any correspondence related to the loan.</p>

<p>This authorization is valid for <strong>$valid_days days</strong> from the date
above and may be revoked by me in writing at any time.</p>

<div class="siggrid">
<div><p><strong>Borrower:</strong> $seller_name</p><p class="sigline">Signature / Date</p></div>
</div>

<p><strong>Borrower SSN (last 4):</strong> $ssn_last4<br>
<strong>Borrower date of birth:</strong> $dob<br>
<strong>Borrower phone:</strong> $seller_phone</p>""")

# ---------------------------------------------------------------------------
# 9. Proof of Funds Letter
# ---------------------------------------------------------------------------
PROOF_OF_FUNDS = Template("""<h2>Proof of Funds</h2>
<p class="muted">Dated <strong>$date</strong></p>

<p>To whom it may concern,</p>

<p>This letter confirms that <strong>$buyer_name</strong> has verified liquid funds
available in the amount of <strong>$$$funds_amount</strong>, sufficient to close
on the purchase of <strong>$property_address, $city $postal</strong> at the
proposed purchase price of <strong>$$$purchase_price</strong>.</p>

<p>Funds are held in the following account(s):</p>
<p><strong>Account holder:</strong> $account_holder<br>
<strong>Institution:</strong> $institution<br>
<strong>Account type:</strong> $account_type</p>

<p>This verification is current as of the date above. Account numbers are
available to the title company or closing attorney upon request.</p>

<p>Sincerely,</p>
<p><strong>$verifier_name</strong><br>
$verifier_title<br>
$institution<br>
$verifier_phone</p>

<div class="siggrid">
<div><p><strong>Verified by:</strong></p><p class="sigline">Signature / Date</p></div>
</div>""")

# ---------------------------------------------------------------------------
# 10. Cancellation / Termination Agreement
# ---------------------------------------------------------------------------
CANCELLATION_AGREEMENT = Template("""<h2>Mutual Cancellation and Release of Purchase Agreement</h2>
<p class="muted">Dated <strong>$date</strong></p>
<p><strong>Seller:</strong> $seller_name<br>
<strong>Buyer:</strong> $buyer_name<br>
<strong>Property:</strong> $property_address, $city $postal<br>
<strong>Original agreement date:</strong> $original_agreement_date</p>

<ol>
<li><strong>Cancellation.</strong> The parties mutually agree to cancel and terminate the purchase agreement dated $original_agreement_date for the Property described above (the "Agreement").</li>

<li><strong>Earnest money.</strong> The earnest money deposit of <strong>$$$earnest_amount</strong> held by $escrow_holder shall be: $earnest_disposition.</li>

<li><strong>Mutual release.</strong> Upon execution of this cancellation, both parties release each other from all obligations, claims, and liabilities arising from the Agreement, except for obligations that expressly survive termination.</li>

<li><strong>No further claims.</strong> Neither party will pursue any claim against the other related to the Agreement or the Property transaction contemplated by it.</li>

<li><strong>Entire agreement.</strong> This document is the entire agreement regarding cancellation of the Agreement.</li>
</ol>

<div class="siggrid">
<div><p><strong>Seller:</strong> $seller_name</p><p class="sigline">Signature / Date</p></div>
<div><p><strong>Buyer:</strong> $buyer_name</p><p class="sigline">Signature / Date</p></div>
</div>""")

# ---------------------------------------------------------------------------
# Template registry
# ---------------------------------------------------------------------------
TEMPLATES = [
    {
        "id": "purchase_agreement",
        "title": "Wholesale Purchase Agreement",
        "category": "Core Deal Documents",
        "when_to_use": "Use this to lock up the deal with the seller. This is the main contract: as-is, assignable, with an inspection period so you can walk away. Get this signed before anything else.",
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
            {"name": "earnest_days", "label": "Earnest due within (business days)", "default": "3"},
            {"name": "escrow_holder", "label": "Escrow / title holder", "default": ""},
            {"name": "closing_date", "label": "Closing date", "default": ""},
            {"name": "inspection_days", "label": "Inspection days", "default": "10"},
            {"name": "disclosures", "label": "Seller disclosures (defects, liens, notices)", "default": "None disclosed."},
            {"name": "personal_property", "label": "Personal property included", "default": "None."},
            {"name": "date", "label": "Agreement date", "from": "today"},
        ],
    },
    {
        "id": "assignment",
        "title": "Assignment of Contract",
        "category": "Core Deal Documents",
        "when_to_use": "Use this when you have an end buyer ready. It transfers your purchase agreement to them and locks in your assignment fee, paid from closing proceeds.",
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
        "category": "Core Deal Documents",
        "when_to_use": "Use this every time money changes hands. It proves the deposit was paid, who holds it, and the refund terms. No receipt, no paper trail.",
        "template": EARNEST_RECEIPT,
        "fields": [
            {"name": "buyer_name", "label": "Buyer name", "from": "buyer_default"},
            {"name": "property_address", "label": "Property address", "from": "address"},
            {"name": "city", "label": "City", "from": "city"},
            {"name": "postal", "label": "Postal / ZIP", "from": "postal"},
            {"name": "earnest_amount", "label": "Earnest amount", "default": "500"},
            {"name": "earnest_amount_words", "label": "Amount in words", "default": "Five hundred dollars"},
            {"name": "escrow_holder", "label": "Held by", "default": ""},
            {"name": "original_agreement_date", "label": "Purchase agreement date", "default": ""},
            {"name": "date", "label": "Receipt date", "from": "today"},
        ],
    },
    {
        "id": "letter_of_intent",
        "title": "Letter of Intent (LOI)",
        "category": "Pre-Contract",
        "when_to_use": "Use this to start the conversation when the seller is not ready to sign a full contract yet. It is non-binding, so it gets terms on paper fast and keeps the door open.",
        "template": LETTER_OF_INTENT,
        "fields": [
            {"name": "seller_name", "label": "Seller name", "from": "owner_name"},
            {"name": "property_address", "label": "Property address", "from": "address"},
            {"name": "city", "label": "City", "from": "city"},
            {"name": "postal", "label": "Postal / ZIP", "from": "postal"},
            {"name": "buyer_name", "label": "Buyer name", "from": "buyer_default"},
            {"name": "purchase_price", "label": "Proposed price", "from": "offer_amount"},
            {"name": "earnest_amount", "label": "Proposed earnest money", "default": "500"},
            {"name": "inspection_days", "label": "Inspection days", "default": "10"},
            {"name": "closing_date", "label": "Target closing date", "default": ""},
            {"name": "agreement_days", "label": "Days to prepare formal agreement", "default": "3"},
            {"name": "date", "label": "Date", "from": "today"},
        ],
    },
    {
        "id": "option_agreement",
        "title": "Option Agreement",
        "category": "Pre-Contract",
        "when_to_use": "Use this when you need exclusive control of a property without committing to buy. You pay a small option fee for the sole right to purchase within a set window. Good for uncertain deals or when you need time to find a buyer.",
        "template": OPTION_AGREEMENT,
        "fields": [
            {"name": "seller_name", "label": "Seller (optionor)", "from": "owner_name"},
            {"name": "property_address", "label": "Property address", "from": "address"},
            {"name": "city", "label": "City", "from": "city"},
            {"name": "postal", "label": "Postal / ZIP", "from": "postal"},
            {"name": "buyer_name", "label": "Buyer (optionee)", "from": "buyer_default"},
            {"name": "option_fee", "label": "Option fee", "default": "100"},
            {"name": "option_days", "label": "Option period (days)", "default": "30"},
            {"name": "purchase_price", "label": "Purchase price if exercised", "from": "offer_amount"},
            {"name": "closing_days", "label": "Days to close after exercise", "default": "14"},
            {"name": "date", "label": "Date", "from": "today"},
        ],
    },
    {
        "id": "memorandum_of_agreement",
        "title": "Memorandum of Agreement",
        "category": "Deal Protection",
        "when_to_use": "Use this right after the purchase agreement is signed. Recording it clouds the title so the seller cannot sell to someone else behind your back. Record it at the county or land titles office.",
        "template": MEMORANDUM_OF_AGREEMENT,
        "fields": [
            {"name": "seller_name", "label": "Seller name", "from": "owner_name"},
            {"name": "buyer_name", "label": "Buyer name", "from": "buyer_default"},
            {"name": "property_address", "label": "Property address", "from": "address"},
            {"name": "city", "label": "City", "from": "city"},
            {"name": "postal", "label": "Postal / ZIP", "from": "postal"},
            {"name": "legal_description", "label": "Legal description (from title search)", "default": ""},
            {"name": "original_agreement_date", "label": "Purchase agreement date", "default": ""},
            {"name": "date", "label": "Date", "from": "today"},
        ],
    },
    {
        "id": "joint_venture",
        "title": "Joint Venture Agreement",
        "category": "Partnerships",
        "when_to_use": "Use this when partnering with another wholesaler on a deal. It spells out who does what, who pays what, and exactly how the profit is split, so nobody argues at closing.",
        "template": JOINT_VENTURE,
        "fields": [
            {"name": "partner_a_name", "label": "Partner A name", "from": "buyer_default"},
            {"name": "partner_b_name", "label": "Partner B name", "default": ""},
            {"name": "property_address", "label": "Property address", "from": "address"},
            {"name": "city", "label": "City", "from": "city"},
            {"name": "postal", "label": "Postal / ZIP", "from": "postal"},
            {"name": "partner_a_role", "label": "Partner A responsibilities", "default": "Contract acquisition and seller communication."},
            {"name": "partner_b_role", "label": "Partner B responsibilities", "default": "Buyer marketing and disposition."},
            {"name": "partner_a_contribution", "label": "Partner A contribution", "default": ""},
            {"name": "partner_b_contribution", "label": "Partner B contribution", "default": ""},
            {"name": "partner_a_split", "label": "Partner A profit %", "default": "50"},
            {"name": "partner_b_split", "label": "Partner B profit %", "default": "50"},
            {"name": "end_date", "label": "Venture end date", "default": ""},
            {"name": "date", "label": "Date", "from": "today"},
        ],
    },
    {
        "id": "authorization_release",
        "title": "Authorization to Release Information",
        "category": "Pre-Foreclosure",
        "when_to_use": "Use this on every pre-foreclosure deal. It lets you talk to the seller's lender about the loan balance, payoff, reinstatement amount, and foreclosure timeline. Without it, the lender will not talk to you.",
        "template": AUTHORIZATION_RELEASE,
        "fields": [
            {"name": "seller_name", "label": "Borrower (seller) name", "from": "owner_name"},
            {"name": "seller_phone", "label": "Borrower phone", "from": "owner_phone"},
            {"name": "property_address", "label": "Property address", "from": "address"},
            {"name": "city", "label": "City", "from": "city"},
            {"name": "postal", "label": "Postal / ZIP", "from": "postal"},
            {"name": "buyer_name", "label": "Authorized party (you)", "from": "buyer_default"},
            {"name": "lender_name", "label": "Lender / servicer name", "default": ""},
            {"name": "loan_number", "label": "Loan number", "default": ""},
            {"name": "valid_days", "label": "Valid for (days)", "default": "90"},
            {"name": "ssn_last4", "label": "Borrower SSN last 4", "default": ""},
            {"name": "dob", "label": "Borrower date of birth", "default": ""},
            {"name": "date", "label": "Date", "from": "today"},
        ],
    },
    {
        "id": "proof_of_funds",
        "title": "Proof of Funds Letter",
        "category": "Credibility",
        "when_to_use": "Use this to show a seller you can actually close. Attach it to your offer so the seller takes you seriously, especially on competitive or listed deals.",
        "template": PROOF_OF_FUNDS,
        "fields": [
            {"name": "buyer_name", "label": "Buyer name", "from": "buyer_default"},
            {"name": "property_address", "label": "Property address", "from": "address"},
            {"name": "city", "label": "City", "from": "city"},
            {"name": "postal", "label": "Postal / ZIP", "from": "postal"},
            {"name": "funds_amount", "label": "Verified funds amount", "default": ""},
            {"name": "purchase_price", "label": "Proposed purchase price", "from": "offer_amount"},
            {"name": "account_holder", "label": "Account holder", "from": "buyer_default"},
            {"name": "institution", "label": "Bank / institution", "default": ""},
            {"name": "account_type", "label": "Account type", "default": "Checking"},
            {"name": "verifier_name", "label": "Verifier name", "default": ""},
            {"name": "verifier_title", "label": "Verifier title", "default": ""},
            {"name": "verifier_phone", "label": "Verifier phone", "default": ""},
            {"name": "date", "label": "Date", "from": "today"},
        ],
    },
    {
        "id": "cancellation_agreement",
        "title": "Cancellation / Termination Agreement",
        "category": "Exit",
        "when_to_use": "Use this to exit a deal cleanly. It cancels the purchase agreement, settles the earnest money, and releases both sides so nobody can come back later with a claim.",
        "template": CANCELLATION_AGREEMENT,
        "fields": [
            {"name": "seller_name", "label": "Seller name", "from": "owner_name"},
            {"name": "buyer_name", "label": "Buyer name", "from": "buyer_default"},
            {"name": "property_address", "label": "Property address", "from": "address"},
            {"name": "city", "label": "City", "from": "city"},
            {"name": "postal", "label": "Postal / ZIP", "from": "postal"},
            {"name": "original_agreement_date", "label": "Original agreement date", "default": ""},
            {"name": "earnest_amount", "label": "Earnest money amount", "default": "500"},
            {"name": "escrow_holder", "label": "Earnest money held by", "default": ""},
            {"name": "earnest_disposition", "label": "Earnest money goes to", "default": "be refunded to Buyer in full within 5 business days."},
            {"name": "date", "label": "Date", "from": "today"},
        ],
    },
]


def get_template(tid: str) -> dict | None:
    return next((t for t in TEMPLATES if t["id"] == tid), None)


def templates_by_category() -> dict:
    """Group templates under their category, preserving CATEGORIES order."""
    grouped = {c: [] for c in CATEGORIES}
    for t in TEMPLATES:
        grouped.setdefault(t["category"], []).append(t)
    return {c: ts for c, ts in grouped.items() if ts}


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
    return template["template"].safe_substitute(safe) + DISCLAIMER_HTML
