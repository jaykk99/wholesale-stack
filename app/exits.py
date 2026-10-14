"""Exit strategies: every way to make money on a property, with per-deal math.

All numbers are estimates from the lead's ARV, asking price, and repair
estimate. Plain English, no em dashes.
"""


def _money(x) -> str:
    try:
        return "${:,}".format(round(float(x)))
    except (TypeError, ValueError):
        return "n/a"


def _pmt(principal: float, annual_rate: float, years: int) -> float:
    """Monthly loan payment."""
    r = annual_rate / 12
    n = years * 12
    if r <= 0:
        return principal / n if n else 0
    return principal * r * (1 + r) ** n / ((1 + r) ** n - 1)


def exit_strategies(lead: dict) -> list[dict]:
    """Return the 8 exit strategies with math for this property."""
    try:
        arv = float(lead.get("arv_estimate") or 0)
        asking = float(lead.get("asking_price") or 0)
        repairs = float(lead.get("repair_estimate") or 0)
    except (TypeError, ValueError):
        return []
    if not arv:
        return []

    buy = asking if asking else arv * 0.70 - repairs  # fall back to MAO
    mao = arv * 0.70 - repairs
    spread = mao - buy if asking else 0
    strategies = []

    # 1. Wholesale assignment - no money needed, fastest
    strategies.append({
        "id": "assignment",
        "title": "Wholesale Assignment",
        "how": "You get the house under contract, then sell the contract itself to a cash buyer. You never own the house. Your profit is the assignment fee, paid to you at closing.",
        "math": [
            ("Your contract price", _money(buy)),
            ("Assignment fee (your profit)", _money(max(spread, 0))),
            ("End buyer pays", _money(buy + max(spread, 0))),
            ("Money out of your pocket", "$0"),
        ],
        "pros": ["No money needed", "Fast, often 2 to 4 weeks", "No risk of owning the house"],
        "cons": ["Need a buyer lined up", "Smaller profit than flipping", "Seller sees your fee on the closing statement"],
        "contract_id": "assignment",
        "ready": asking > 0 and spread > 0,
        "no_money": True,
        "speed": "7-21 days",
        "speed_days": 14,
    })

    # 2. Novation - no money needed
    list_nov = arv * 0.95
    nov_costs = 2000
    profit_nov = list_nov - buy - nov_costs
    strategies.append({
        "id": "novation",
        "title": "Novation",
        "how": "The seller signs an agreement letting you market their house and find the buyer. You list it, bring the buyer, and keep everything above the agreed price. Cleaner than assignment because you control the sale.",
        "math": [
            ("Agreed price with seller", _money(buy)),
            ("You list and sell for", _money(list_nov)),
            ("Marketing + closing", _money(nov_costs)),
            ("Your profit", _money(profit_nov)),
        ],
        "pros": ["No money needed", "Bigger fees than assignment", "No buyer list needed upfront", "Seller is cooperative by design"],
        "cons": ["Takes longer than assignment", "You pay for marketing", "Needs MLS access or an agent partner"],
        "contract_id": "memorandum_of_agreement",
        "ready": asking > 0 and profit_nov > 0,
        "no_money": True,
        "speed": "30-60 days",
        "speed_days": 45,
    })

    # 3. Double close
    sell_dc = arv * 0.95
    close_buy = buy * 0.02
    close_sell = sell_dc * 0.02
    profit_dc = sell_dc - buy - close_buy - close_sell
    strategies.append({
        "id": "double_close",
        "title": "Double Close",
        "how": "You actually buy the house, then sell it to your end buyer hours or days later in a second closing. The seller never sees your profit. Costs more in closing fees but keeps your spread private.",
        "math": [
            ("You buy for", _money(buy)),
            ("You sell for", _money(sell_dc)),
            ("Two closings cost", _money(close_buy + close_sell)),
            ("Your profit", _money(profit_dc)),
        ],
        "pros": ["Profit stays private", "Seller cannot back out over your fee", "Works when assignment fees look too big"],
        "cons": ["Two sets of closing costs", "Need short term funding for the first close", "Tight timing between closings"],
        "contract_id": "purchase_agreement",
        "ready": asking > 0 and profit_dc > 0,
        "no_money": False,
        "speed": "14-30 days",
        "speed_days": 21,
    })

    # 4. Lease option - little money down
    opt_fee = arv * 0.04
    mkt_rent = arv * 0.008
    lease_to_seller = mkt_rent
    rent_from_tenant = mkt_rent * 1.10
    mo_spread = rent_from_tenant - lease_to_seller
    backend = arv - buy
    total_lo = opt_fee + mo_spread * 12 + backend
    strategies.append({
        "id": "lease_option",
        "title": "Lease Option",
        "how": "You lease the house from the seller with the right to buy it later, then lease it to a tenant buyer at a higher rent with the right to buy from you. You profit three ways: an upfront option fee, a monthly rent spread, and the backend price difference.",
        "math": [
            ("Option fee upfront", _money(opt_fee)),
            ("Monthly rent spread", _money(mo_spread)),
            ("Backend profit at sale", _money(backend)),
            ("Total profit (1 yr)", _money(total_lo)),
        ],
        "pros": ["Three profit streams", "Little money down", "Tenant buyer handles maintenance"],
        "cons": ["Complex paperwork", "Two deals to manage", "Tenant buyer may not close"],
        "contract_id": "option_agreement",
        "ready": asking > 0 and backend > 0,
        "no_money": False,
        "speed": "14-30 days",
        "speed_days": 21,
    })

    # 5. Wholetail
    cleanup = 3000
    list_wt = arv * 0.95
    realtor = list_wt * 0.05
    close_wt = list_wt * 0.02
    profit_wt = list_wt - buy - cleanup - realtor - close_wt
    strategies.append({
        "id": "wholetail",
        "title": "Wholetail",
        "how": "Buy it, do a light cleanup (paint, trash out, landscaping), then list it on the MLS like a normal sale. Faster than a full flip and bigger profit than wholesaling.",
        "math": [
            ("Buy", _money(buy)),
            ("Light cleanup", _money(cleanup)),
            ("List on MLS for", _money(list_wt)),
            ("Realtor + closing", _money(realtor + close_wt)),
            ("Your profit", _money(profit_wt)),
        ],
        "pros": ["Bigger than wholesale profit", "Fast, no big reno", "Retail buyers pay more"],
        "cons": ["Need a listing agent", "Market can shift while listed", "Carrying costs if it sits"],
        "contract_id": "purchase_agreement",
        "ready": asking > 0 and profit_wt > 0,
        "no_money": False,
        "speed": "30-90 days",
        "speed_days": 60,
    })

    # 6. Buy and hold
    down = buy * 0.20
    loan = buy * 0.80
    pi = _pmt(loan, 0.07, 30)
    rent = arv * 0.008
    expenses = rent * 0.40
    cashflow = rent - expenses - pi
    cap_rate = (rent * 12 * 0.60) / buy * 100 if buy else 0
    coc = (cashflow * 12) / down * 100 if down else 0
    strategies.append({
        "id": "buy_hold",
        "title": "Buy and Hold (Rental)",
        "how": "Buy it and rent it out. Tenants pay the mortgage while the house gains value over the years. You get monthly cash flow plus long term appreciation.",
        "math": [
            ("Down payment (20%)", _money(down)),
            ("Monthly rent estimate", _money(rent)),
            ("Monthly mortgage (P+I)", _money(pi)),
            ("Monthly cash flow", _money(cashflow)),
            ("Cap rate", f"{cap_rate:.1f}%"),
            ("Cash on cash return", f"{coc:.1f}%"),
        ],
        "pros": ["Monthly income", "Tenants build your equity", "Tax benefits on rentals"],
        "cons": ["Landlord work or property manager cost", "Money tied up for years", "Vacancy and repair risk"],
        "contract_id": "purchase_agreement",
        "ready": asking > 0 and cashflow > 0,
        "no_money": False,
        "speed": "30-45 days",
        "speed_days": 37,
    })

    # 7. Seller financing
    sell_sf = arv
    down_sf = sell_sf * 0.10
    bal = sell_sf - down_sf
    mo_sf = _pmt(bal, 0.08, 15)
    total_in = down_sf + mo_sf * 180
    profit_sf = total_in - buy
    strategies.append({
        "id": "seller_financing",
        "title": "Seller Financing",
        "how": "You sell the house and act as the bank. The buyer gives you a down payment, then pays you every month with interest. You collect more than the sale price over time.",
        "math": [
            ("Sale price", _money(sell_sf)),
            ("Down payment to you", _money(down_sf)),
            ("Monthly payment to you", _money(mo_sf)),
            ("Total collected over 15 yrs", _money(total_in)),
            ("Extra vs cash sale", _money(profit_sf)),
        ],
        "pros": ["Higher total profit than cash sale", "Monthly income for years", "Sells faster, bigger buyer pool"],
        "cons": ["Buyer might default", "Money comes in slowly", "Need a proper promissory note and mortgage"],
        "contract_id": "purchase_agreement",
        "ready": asking > 0,
        "no_money": False,
        "speed": "30-60 days",
        "speed_days": 45,
    })

    # 8. Fix and flip
    sell_flip = arv
    purchase_close = buy * 0.02
    holding = buy * 0.006 * 6  # 6 months carry
    selling_cost = sell_flip * 0.06  # realtor + closing
    profit_flip = sell_flip - buy - repairs - purchase_close - holding - selling_cost
    strategies.append({
        "id": "fix_flip",
        "title": "Fix and Flip",
        "how": "Buy it, renovate it, sell it at full retail price. This is the biggest profit of any strategy, but you need renovation money and it takes months.",
        "math": [
            ("Buy", _money(buy)),
            ("Renovation", _money(repairs)),
            ("Sell at ARV", _money(sell_flip)),
            ("Closing + holding + realtor", _money(purchase_close + holding + selling_cost)),
            ("Your profit", _money(profit_flip)),
        ],
        "pros": ["Highest profit", "You control the whole deal", "Builds a track record with lenders"],
        "cons": ["Needs capital for buy + reno", "Renovation surprises happen", "Takes 3 to 6 months"],
        "contract_id": "purchase_agreement",
        "ready": asking > 0 and profit_flip > 0,
        "no_money": False,
        "speed": "3-6 months",
        "speed_days": 135,
    })

    # Sort: no-money strategies first (by speed), then the rest (by speed)
    strategies.sort(key=lambda s: (0 if s["no_money"] else 1, s["speed_days"]))
    return strategies
