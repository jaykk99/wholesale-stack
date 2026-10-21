"""Deal analyzer: wholesaling offer math as pure functions.

MAO (maximum allowable offer) = ARV x 0.70 - repairs - closing/holding costs.
Spread = MAO - asking price. The spread is the room for the assignment fee.

Nothing here moves money or contacts anyone; it is arithmetic for evaluating
whether a lead is worth pursuing.
"""

from typing import Any


def parse_money(v: Any) -> float:
    """Parse loose money input ('250k', '$185,000', 185000) to a float."""
    if v is None:
        return 0.0
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip().lower().replace("$", "").replace(",", "").replace(" ", "")
    if not s:
        return 0.0
    mult = 1.0
    if s.endswith("k"):
        mult = 1000.0
        s = s[:-1]
    elif s.endswith("m"):
        mult = 1_000_000.0
        s = s[:-1]
    try:
        return float(s) * mult
    except ValueError:
        return 0.0


def analyze(arv: Any, asking: Any, repairs: Any = 0, closing_costs: Any = 0,
            holding_costs: Any = 0, desired_fee: Any = 10000) -> dict:
    """Run the full deal analysis. Returns a dict with every number shown."""
    arv = parse_money(arv)
    asking = parse_money(asking)
    repairs = parse_money(repairs)
    closing_costs = parse_money(closing_costs)
    holding_costs = parse_money(holding_costs)
    desired_fee = parse_money(desired_fee) or 10000

    ready = arv > 0
    mao = round(arv * 0.70 - repairs - closing_costs - holding_costs) if ready else 0
    spread = round(mao - asking) if (ready and asking) else 0
    # Offer that leaves the desired fee intact: offer + fee must fit under MAO.
    offer_for_fee = round(mao - desired_fee) if ready else 0
    # If the seller accepted MAO, the fee captured is the spread.
    fee_at_asking = spread if asking else 0

    if not ready:
        verdict, verdict_detail = "need-arv", "Enter the after-repair value to analyze this deal."
    elif spread >= desired_fee:
        verdict = "deal"
        verdict_detail = (
            "The spread covers your target fee with room to spare. "
            "This is worth an offer."
        )
    elif spread >= desired_fee * 0.5:
        verdict = "thin"
        verdict_detail = (
            "The spread is thin. It can still work if repairs come in low or "
            "the seller flexes on price, but negotiate hard."
        )
    elif spread > 0:
        verdict = "tight"
        verdict_detail = (
            "Barely any room. Only pursue if you can get the price down or "
            "shave repair costs with your own numbers."
        )
    else:
        verdict = "no-deal"
        verdict_detail = (
            "The asking price is above what the numbers support. "
            "Walk away or follow up later if the seller gets motivated."
        )

    lines = []
    if ready:
        lines = [
            ("After-repair value (ARV)", arv),
            ("Investor discount (70% rule)", round(arv * 0.70)),
            ("Less: repairs", -repairs),
            ("Less: closing costs", -closing_costs),
            ("Less: holding costs", -holding_costs),
            ("Maximum allowable offer", mao),
        ]
        if asking:
            lines.append(("Less: asking price", -asking))
            lines.append(("Spread (room for your fee)", spread))

    return {
        "ready": ready,
        "arv": round(arv),
        "asking": round(asking),
        "repairs": round(repairs),
        "closing_costs": round(closing_costs),
        "holding_costs": round(holding_costs),
        "desired_fee": round(desired_fee),
        "mao": mao,
        "spread": spread,
        "offer_for_fee": offer_for_fee,
        "fee_at_asking": fee_at_asking,
        "verdict": verdict,
        "verdict_detail": verdict_detail,
        "lines": [(label, round(v)) for label, v in lines],
    }


def fmt(n: float) -> str:
    """Format a dollars figure for templates: 185000 -> $185,000."""
    sign = "-" if n < 0 else ""
    return f"{sign}${abs(round(n)):,}"
