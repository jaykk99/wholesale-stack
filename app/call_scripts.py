"""Call script library. Each script is tied to the pipeline stages where it is useful,
so the lead page always shows the right script for where the deal stands."""

SCRIPTS = [
    {
        "id": "cold_call",
        "title": "Initial Cold Call",
        "stages": ["new", "contacted"],
        "goal": "Find out if they are open to selling and book a time to see the property.",
        "body": """Hi, is this [NAME]?

My name is [YOUR NAME], I am calling about the property at [ADDRESS]. I buy houses in the area and I wanted to check if you have ever thought about selling it.

[If yes / maybe:]
Great. Can I ask a couple quick questions so I do not waste your time?

1. What kind of shape is the place in right now?
2. Is it rented, vacant, or are you living there?
3. If you did sell, what kind of timeline would you be looking at?
4. Do you have a number in mind you would need to get?

[If they give a number:]
Okay, I appreciate that. Here is how I work: I would like to come take a quick look, then I can give you a firm cash offer, usually within 24 hours. No fees, no commissions, I cover closing costs. Would [DAY] morning or afternoon work better for a 15 minute walkthrough?

[If no / not interested:]
No problem at all. If anything changes down the road, can I check back with you in a few months?""",
    },
    {
        "id": "follow_up",
        "title": "Follow-Up Call",
        "stages": ["contacted", "appointment"],
        "goal": "Re-engage a warm lead and move them toward a viewing or an offer.",
        "body": """Hi [NAME], it is [YOUR NAME] calling back about [ADDRESS].

Last time we talked you mentioned [REFERENCE: timeline / price / situation]. I have been thinking about your place and I wanted to check in, has anything changed on your end?

[If still interested:]
Good. I would like to move this forward for you. The next step is a quick 15 minute walkthrough so I can make you a firm offer. I have [DAY] or [DAY] open, which is better?

[If still on the fence:]
That is fine, there is no pressure here. Most people I talk to just want to know what their options are. Would it help if I gave you a ballpark number first, and then you decide if a walkthrough is worth it?

[Before hanging up, always:]
Just so I have it right, the best number to reach you is still [PHONE], correct? And is there a better time of day to call?""",
    },
    {
        "id": "objection_price",
        "title": "Objection: Price Too Low",
        "stages": ["offer", "negotiation"],
        "goal": "Keep the conversation alive when they say your offer is too low.",
        "body": """I understand, [NAME]. Can I ask, what number were you hoping to get?

[Listen. Repeat their number back.]

Okay, so you are at [THEIR NUMBER] and I am at [YOUR OFFER]. Help me understand something: if you listed it with an agent at your number, after commissions, closing costs, and a few months of carrying costs, what do you figure you would actually walk away with?

[Let them think.]

The reason my offer is where it is: I am buying as-is, no repairs, no showings, no waiting on bank approvals, and I can close on your timeline. A lot of sellers find the net number ends up pretty close once you subtract all of that.

Is the price the only thing holding this up, or is there something else? If we could get closer on the number, are you ready to move forward?""",
    },
    {
        "id": "objection_just_looking",
        "title": "Objection: Just Looking / Not Sure About Selling",
        "stages": ["contacted", "appointment", "negotiation"],
        "goal": "Turn a maybe into a clear next step without pressure.",
        "body": """That is completely fine, [NAME]. Most people I talk to are just exploring their options at first.

Can I ask you straight: on a scale of 1 to 10, how serious are you about selling in the next few months? A 1 means not at all, 10 means let us get it done.

[If 6 or higher:]
Okay, so there is some real interest there. What would need to happen to get that to an 8 or 9? Usually it is either the number or the timing. Which one is it for you?

[If 5 or lower:]
I appreciate the honesty. Here is what I suggest: let me give you my number, and I will check back in [TIMEFRAME]. If your situation changes, you already know someone who buys as-is with no hassle. Fair enough?

[Either way, end with:]
Is it okay if I follow up with you then?""",
    },
    {
        "id": "objection_spouse",
        "title": "Objection: Need Spouse / Partner Approval",
        "stages": ["offer", "negotiation"],
        "goal": "Get both decision makers in the same conversation.",
        "body": """Of course, [NAME]. That is a big decision and you should both be comfortable.

Here is what usually works best: instead of you trying to explain my whole offer secondhand, can we get [SPOUSE NAME] on the phone together for five minutes? I will walk through the numbers once, answer any questions, and then you two can talk it over with the full picture.

Would tonight or tomorrow evening work for a quick three-way call?

[If they resist:]
I get it. Then let me ask: if your [husband/wife/partner] was on board, is this something YOU would want to do? I just want to know where you stand personally.

[If yes:]
Good. Then let us get them looped in so you are deciding together with all the facts. What time works?""",
    },
    {
        "id": "objection_timeline",
        "title": "Objection: Bad Timing / Need More Time",
        "stages": ["contacted", "appointment", "negotiation"],
        "goal": "Pin down the real timeline and stay in the picture.",
        "body": """No rush at all, [NAME]. I would rather do this on your timeline than push you.

Can I ask, when you picture this happening, what month are we talking about? [MONTH]?

[Whatever they say:]

Okay. Here is what I can do: I will put you in my calendar to check back [2 WEEKS BEFORE THEIR MONTH]. That way you are not dealing with this hanging over you, and when the time is right we can move fast.

One question so I am ready when we talk next: is there anything about the property I should know now, like repairs it needs or tenants in place? It helps me come back with a real number instead of starting over.

And just so I do not lose you, is [PHONE] still the best number?""",
    },
    {
        "id": "make_offer",
        "title": "Making the Offer",
        "stages": ["appointment", "offer"],
        "goal": "Present the cash offer clearly and ask for the deal.",
        "body": """[NAME], I have been through the property and run my numbers. Here is where I land:

I can offer you $[OFFER] cash, as-is. That means:
- No repairs, I take it exactly as it sits
- No agent commissions or fees
- I cover standard closing costs
- We close on your timeline, [DATE] works on my end

I know it is below what a fixed-up house sells for, and that is because I am taking on all the repair risk and the holding costs. What you get is certainty and speed.

So the question is: does $[OFFER] work for you?

[If yes:]
Excellent. I will send over a simple one-page purchase agreement today. Once you sign, we open escrow and I handle everything from there. What email should I send it to?

[If they hesitate:]
What part is not sitting right, the number or the timing? Let us talk through it.""",
    },
    {
        "id": "closing",
        "title": "Closing / Next Steps",
        "stages": ["closed_won", "negotiation"],
        "goal": "Lock in the agreement and keep the deal on rails to closing.",
        "body": """[NAME], great, we have a deal at $[OFFER]. Here is exactly what happens next:

1. I send you the purchase agreement today. It is one page, plain language.
2. You sign and send it back. No money changes hands yet.
3. I open escrow with [TITLE COMPANY]. They handle all the paperwork.
4. We do a quick title check, usually [X] days.
5. We close on or before [DATE]. You get your money, I get the keys.

Two things I need from you today: the signed agreement, and a good time for [TITLE COMPANY] to reach you for ID verification.

[If anything feels off:]
Tell me straight, is there anything that would stop this from closing? I would rather hear it now so we can fix it together.

Thank you for trusting me with this, [NAME]. I will make this as smooth as I can.""",
    },
]


def scripts_for_stage(stage: str) -> list[dict]:
    return [s for s in SCRIPTS if stage in s["stages"]]


def get_script(script_id: str) -> dict | None:
    for s in SCRIPTS:
        if s["id"] == script_id:
            return s
    return None
