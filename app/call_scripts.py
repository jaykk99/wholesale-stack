"""Call script library. Each script is tied to the pipeline stages where it is useful,
so the lead page always shows the right script for where the deal stands.

Written for Amanda: natural, conversational, with stage directions in [brackets].
Read the directions, say the rest out loud in your own words. You do not need
to memorize these. Just follow the flow."""

SCRIPTS = [
    {
        "id": "cold_call",
        "title": "Cold Call to Seller",
        "stages": ["new", "contacted"],
        "goal": "Start a friendly conversation, find out if they want to sell, and book a property visit.",
        "body": """[Before you dial: take a breath, smile, and have the lead open in the app so you can see the address.]

OPENING:
"Hi, is this [NAME]?"

[If yes:]
"Hi [NAME], my name is Amanda. I am calling about the house at [ADDRESS]. I buy houses in the area, and I was wondering if you have ever thought about selling it?"

[Pause and listen. Let them talk. Do not rush.]

[If they say YES or MAYBE or TELL ME MORE:]
"Great, I appreciate you talking with me. Can I ask you a couple quick questions so I do not waste your time?"

QUALIFYING QUESTIONS (ask warmly, like a conversation, not an interrogation):
1. "What kind of shape is the place in right now?"
   [Listen. Write down what they say.]
2. "Is it rented, vacant, or are you living there?"
3. "If you did sell, what kind of timeline would you be looking at?"
4. "Do you have a number in mind that you would need to get for it?"
   [If they give a number, repeat it back: "Okay, so around $[NUMBER], got it."]

[If they ask HOW MUCH WILL YOU OFFER:]
"I would love to give you a real number, and to do that fairly I need to see the place first. Here is how I work: I come take a quick 15 minute look, then I give you a firm cash offer within 24 hours. No fees, no commissions, I cover the closing costs. Would [DAY] morning or afternoon work better for you?"

[If they say NO or NOT INTERESTED:]
"No problem at all, I understand. Can I ask one quick thing: if anything changes down the road, would it be okay if I check back with you in a few months?"
[If yes: "Thank you, [NAME]. I will talk to you then." Log it as a follow up.]

[If they ask HOW DID YOU GET MY NUMBER:]
"That is a fair question. I look for houses in the area that owners might want to sell, and yours came up. I am happy to take you off my list if you would like."

[If they ask ARE YOU AN AGENT:]
"No, I am not an agent. I am a local buyer. I buy houses directly with cash, as is. No commissions, no fees, no waiting on bank approvals."

CLOSING THE CALL:
"Thank you for your time, [NAME]. Just so I have it right, is [PHONE] still the best number to reach you?"
[Confirm and log everything in the app right after you hang up.]""",
    },
    {
        "id": "follow_up",
        "title": "Follow-Up Call",
        "stages": ["contacted", "appointment"],
        "goal": "Re-engage a warm lead and move them toward a visit or an offer.",
        "body": """[Before you dial: read your notes from the last call. Know their name, situation, and what they said last time.]

OPENING:
"Hi [NAME], it is Amanda calling back about the house at [ADDRESS]. How are you doing today?"

[Small talk for 30 seconds. Be a person first.]

"Last time we talked you mentioned [REFERENCE: their timeline, price, or situation]. I have been thinking about your place and I wanted to check in. Has anything changed on your end?"

[Pause and listen. This is where deals happen.]

[If they are MORE INTERESTED now:]
"That is good to hear. I would love to move this forward for you. The next step is just a quick 15 minute walkthrough so I can give you a firm offer. I have [DAY] or [DAY] open. Which works better for you?"

[If they are STILL ON THE FENCE:]
"That is completely fine, no pressure at all. Most people I talk to just want to know their options. Would it help if I gave you a ballpark number first? Then you can decide if a walkthrough is even worth your time."

[If they say NOT INTERESTED ANYMORE:]
"I understand, [NAME]. Thank you for being straight with me. If things ever change, you have my number. Would you like me to stop calling, or is it okay to check back in a few months?"
[Respect whatever they say.]

[If they do not answer: leave a voicemail.]
"Hi [NAME], it is Amanda. We talked about your house at [ADDRESS] a little while back. Just checking in to see if anything has changed. My number is [YOUR NUMBER]. No rush at all. Talk soon."

BEFORE YOU HANG UP, ALWAYS:
"Just so I have it right, is [PHONE] still the best number? And is there a better time of day to catch you?"
[Log the call and set the next follow up date in the app.]""",
    },
    {
        "id": "pre_foreclosure_call",
        "title": "Pre-Foreclosure Call",
        "stages": ["new", "contacted"],
        "goal": "Help a homeowner behind on payments understand their options before the bank takes the house.",
        "body": """[Mindset: this person is stressed and probably embarrassed. Be extra kind. You are offering a lifeline, not taking advantage.]

OPENING:
"Hi, is this [NAME]? My name is Amanda. I am calling about the house at [ADDRESS]."

[Pause. They may be guarded. That is normal.]

"I know this might be a sensitive call, so I will be straight with you. I work with homeowners who have fallen behind on their mortgage, and I help them sell before the bank takes the house. I am not with the bank, and I am not a bill collector. I buy houses directly. Is it okay if I take one minute to explain how I might be able to help?"

[If yes, continue. If no, thank them kindly and move on.]

RAPPORT AND QUALIFYING:
"I am sorry you are dealing with this. It happens to good people, and there is no judgment here. Can I ask a few questions so I understand your situation?"

1. "Do you know roughly how far behind the payments are?"
   [Listen without reacting. Write it down.]
2. "Have you gotten any letters from the bank about a sale date?"
   [If yes: "When is that date?" This tells you how urgent it is.]
3. "What do you owe on the mortgage, roughly?"
4. "If you could sell and walk away without owing anything more, would that help you?"

[If they open up:]
"Thank you for trusting me with that. Here is what I can do: I can make you a cash offer and close before the sale date. That stops the foreclosure, protects your credit from getting worse, and in some cases I can even get you some money to walk away with for your next place. Would you like me to take a quick look at the property so I can give you a real number?"

[If they say I AM WORKING IT OUT WITH THE BANK:]
"That is great, I hope that works out for you. Just so you know, I am here as a backup plan if anything changes. Can I check back with you in a couple weeks?"

[If they say THIS IS A SCAM or get angry:]
"I completely understand being cautious. Here is how you stay safe: everything goes through a licensed title company, you never pay me anything, and you can have a lawyer look at everything before you sign. I am just offering you an option. Would it be okay if I sent you my information so you have it?"

CLOSING:
"[NAME], I know this is a lot. The most important thing is that you know you have options, and the sooner we talk numbers, the more options you have. Can we set up a quick 15 minute visit this week?"
[If they agree, move fast. Foreclosure timelines do not wait.]""",
    },
    {
        "id": "probate_call",
        "title": "Probate / Inherited Property Call",
        "stages": ["new", "contacted"],
        "goal": "Gently help someone who inherited a house they do not want to keep.",
        "body": """[Mindset: this person lost someone. Be warm, patient, and human first. Never rush this call.]

OPENING:
"Hi, is this [NAME]? My name is Amanda."

[Pause. Speak softly and slowly.]

"I am calling about the property at [ADDRESS]. I understand it may have belonged to [DECEASED NAME, if you know it]. First, I am sorry for your loss."

[Pause and listen. Let them respond. Do not jump into business.]

"I buy houses in the area, and I work with families who inherited a property and are not sure what to do with it. I am not sure if that is your situation, but if it is, I might be able to make things easier. Is this a good time to talk for a minute?"

[If yes:]
RAPPORT AND QUALIFYING:
"Can I ask, are you the one handling the estate, or is there someone else involved?"
[There may be siblings or other heirs. You need to know who decides.]

1. "What is the condition of the house right now?"
2. "Is anyone living there, or is it sitting empty?"
3. "Has the probate process started, or is that still ahead of you?"
   [If they do not know what probate is: "It is just the legal process of transferring the property. A lawyer handles it. I can wait until that is sorted."]
4. "In a perfect world, what would you like to see happen with the house?"

[Listen carefully. They often want the emotional weight gone more than they want top dollar.]

[If they are interested in selling:]
"I can make this really simple for you. I buy as is, so you do not need to clean it out, fix anything, or even go through everything inside if you do not want to. I handle all of that. I can give you a cash offer and close whenever the legal side is ready. Would it help if I came by to take a look this week?"

[If there are MULTIPLE HEIRS:]
"That is really common. What usually works best is if everyone can be on the same page. Would it help if I explained the offer to everyone at once, so nobody feels left out? I am happy to do a group call."

[If they say IT IS TOO SOON:]
"I completely understand, and there is no rush at all. Grief does not have a timeline. Can I check back with you in a month or two? I will be here whenever you are ready."

CLOSING:
"Thank you for talking with me, [NAME]. I know this is not easy. My number is [YOUR NUMBER] if anything comes up. Take care of yourself."
[Log everything. Set a gentle follow up. These leads often take months but turn into great deals.]""",
    },
    {
        "id": "tired_landlord_call",
        "title": "Tired Landlord Call",
        "stages": ["new", "contacted"],
        "goal": "Connect with a landlord who is burned out and ready to sell their rental.",
        "body": """[Mindset: this person is tired. Tenants, repairs, late rent. They fantasize about being done. You are offering freedom.]

OPENING:
"Hi, is this [NAME]? My name is Amanda. I am calling about the rental property at [ADDRESS]."

[Pause.]

"I work with landlords in the area who are thinking about selling their rentals. I am not sure if that is on your mind, but I wanted to ask: have you ever thought about selling that property?"

[If yes or maybe:]
RAPPORT AND QUALIFYING:
"I talk to a lot of landlords, and honestly most of them tell me the same thing: they are tired. Is that where you are at?"

[Let them vent. Landlords LOVE to complain about tenants. Listen and empathize. "That sounds exhausting" goes a long way.]

1. "How long have you owned it?"
2. "Is it rented right now? How is the tenant situation?"
3. "What is the rent, and what are your monthly costs on it?"
4. "What is the condition like? Any big repairs coming up?"
5. "If you sold, what would you do with your time instead?"
   [This is the dream question. Let them picture life without the headaches.]

[Presenting your solution:]
"Here is what I can do that might be perfect for you: I buy as is, with the tenant in place if you want. You do not need to fix anything, find a new tenant, or deal with showings. I handle all of it. And I can close fast so you are done with it. Would you like me to take a look and give you a cash number?"

[If they say THE TENANT IS A PROBLEM:]
"That is exactly why a lot of landlords sell to me. I deal with the tenant situation after closing. You walk away clean. You do not have to evict anyone or have any awkward conversations."

[If they say I AM NOT SURE WHAT IT IS WORTH:]
"That is what I am here for. Let me come see it, run the numbers, and I will show you exactly how I got to my offer. No obligation. You will at least know what your options are."

[If they say NO:]
"No worries at all. Landlording is not for everyone forever. If you ever get that one tenant that makes you say 'I am done,' you have my number. Can I check back in a few months?"

CLOSING:
"Thanks, [NAME]. Quick question: is [PHONE] the best number for you? I will send you my contact info so you have it."
[Log it. Tired landlords often call back after one more bad tenant month.]""",
    },
    {
        "id": "absentee_owner_call",
        "title": "Absentee Owner Call",
        "stages": ["new", "contacted"],
        "goal": "Reach an owner who does not live at the property and may want to sell it.",
        "body": """[Mindset: this person owns a house they do not live in. It might be vacant, rented, or inherited. They are often emotionally detached from it, which makes them more open to selling.]

OPENING:
"Hi, is this [NAME]? My name is Amanda."

[Pause.]

"I am calling about the house at [ADDRESS]. I see you own it but you are over in [THEIR CITY, if you know it]. I buy houses in that area and I wanted to check if you have ever thought about selling it."

[Pause and listen.]

RAPPORT AND QUALIFYING:
1. "How long have you owned the place?"
2. "What is going on with it right now? Is it rented, vacant, or...?"
   [If vacant: "How long has it been sitting empty?" Vacant houses cost them money every month.]
3. "How is it being taken care of from where you are?"
   [This is the pain point. Managing from far away is hard.]
4. "Have you been out to see it recently?"
5. "If you sold it, is there something you would rather do with the money?"

[If they seem open:]
"Here is why I am calling: owners in your situation usually tell me the house has become more of a headache than an asset. I buy as is, I handle everything locally, and you do not need to travel back for anything. We can do the whole thing remotely. I can give you a cash offer within 24 hours of seeing it. Does that sound worth exploring?"

[If they say I HAVE A PROPERTY MANAGER:]
"That is good, at least someone is watching it. Can I ask honestly: after the management fees and repairs, is it actually making you money? A lot of owners find out it is barely breaking even. If I could get you a fair cash price, would you consider it?"

[If they say I AM KEEPING IT FOR NOW:]
"I understand. Out of curiosity, what would need to change for you to sell it? Sometimes just knowing your number helps for down the road."
[Write down their number. That is gold for follow up.]

[If they say WHO ARE YOU AGAIN / HOW DID YOU GET MY NUMBER:]
"I am a local home buyer, not an agent. I look up property owners in areas where I buy. I am happy to remove you from my list if you would like."

CLOSING:
"Well [NAME], I appreciate your time. Can I send you my contact info in case anything changes? And would it be okay if I checked back in a few months?"
[Log everything. Absentee owners are some of the best leads because distance creates motivation.]""",
    },
    {
        "id": "make_offer",
        "title": "Making the Offer / Closing the Deal",
        "stages": ["appointment", "offer", "negotiation"],
        "goal": "Present the cash offer clearly, handle the response, and get the contract signed.",
        "body": """[Before the call or visit: have your numbers ready. Know your ARV, repair estimate, and maximum offer. Know your walk away number too.]

PRESENTING THE OFFER:
"[NAME], I have been through the property and run my numbers carefully. Here is where I land.

I can offer you $[OFFER] cash, as is. Here is what that means for you:
- No repairs. I take it exactly as it sits.
- No agent commissions or fees.
- I cover the standard closing costs.
- We close on your timeline. [DATE] works on my end.

I know that is below what a fixed up house sells for, and I want to be straight with you about why. I am taking on all the repair costs and the risk, plus the months of holding costs while the work gets done. What you get in return is certainty: cash, no surprises, no waiting on bank approvals."

[Then ask, and WAIT:]
"Does $[OFFER] work for you?"

[Silence. Do not talk. Let them think. The first person to speak loses.]

[If YES:]
"Excellent. I am excited to make this happen for you. I will send over a simple purchase agreement today. It is plain language, one page for the main terms. Once you sign it, I open escrow with the title company and handle everything from there. What is the best email to send it to?"

[If they HESITATE:]
"What part is not sitting right for you? Is it the number, or is it the timing? Let us talk through it."
[Listen. Then address the specific concern. Do not just repeat the offer louder.]

[If they COUNTER with a higher number:]
"Okay, so you are at $[THEIR NUMBER]. Let me be honest with you: my max is $[YOUR MAX]. I cannot go above that and make the numbers work. But let me ask you this: if I could get to $[MIDDLE NUMBER], could we get this done today?"
[Only go up if you have room. Never exceed your maximum offer.]

[If they say I NEED TO THINK ABOUT IT:]
"Of course. Can I ask what you need to think through? If it is the number, I want you to know this is my best offer and I can only hold it for [a few days / until DATE] because I am looking at other properties too. What questions can I answer right now?"

[If they say NO:]
"I appreciate you being straight with me. Can I ask: is it the price, or is there something else? If the price is the issue, what number would work for you?"
[Sometimes no just means not yet. Leave the door open:]
"Okay. If anything changes, I am here. Can I check back with you in [timeframe]?"

GETTING THE SIGNATURE:
Once they agree, move fast. "I am going to send the agreement right now while we are talking. Can you take a look and sign it today? The sooner it is signed, the sooner we can get you to closing."

[After they sign:]
"Thank you for trusting me with this, [NAME]. Here is exactly what happens next:
1. I send the signed agreement to the title company today.
2. They run a title check, usually takes about a week.
3. We close on or before [DATE]. You get your money.
I will keep you updated at every step. You do not need to do anything else."

[Log the offer in the app immediately. Set reminders for every next step.]""",
    },
    {
        "id": "buyer_call",
        "title": "Buyer Call (Presenting a Deal)",
        "stages": ["offer", "negotiation"],
        "goal": "Get a cash buyer excited about your deal and committed with a deposit.",
        "body": """[Before the call: have the deal package ready. Address, photos, your asking price, ARV, repair estimate. Know your numbers cold.]

OPENING:
"Hi [NAME], it is Amanda. I have a deal I think you are going to like. Do you have two minutes?"

[If yes:]
PRESENTING THE DEAL (keep it short, lead with numbers):
"It is a [3 bed 2 bath] at [ADDRESS]. Here are the numbers:
- Asking: $[YOUR PRICE]
- ARV: around $[ARV]
- Repairs: roughly $[REPAIRS]
- That leaves about $[PROFIT] in spread for you.

[Send photos while you talk or right after.]

The house [one sentence on condition: 'needs a full cosmetic rehab' or 'is in rough shape but the structure is solid']. I walked it [yesterday / this week]. What do you think?"

[Pause and listen.]

[If they are INTERESTED:]
"Great. I can set up a walkthrough [DAY] or [DAY]. Which works for you? And just so you know, I do need a non refundable earnest deposit of $[AMOUNT] to hold it for you, since I am taking it off the market. Are you good with that?"

[If they ask for a LOWER PRICE:]
"I hear you. My price is based on the numbers I just showed you. What number works for you?"
[If their number still leaves you a fee you can live with, consider it. If not:]
"I cannot go below $[YOUR MINIMUM] or the deal does not work on my end. But the numbers are solid at my asking price. Want to walk it and see for yourself?"

[If they say SEND ME THE DETAILS:]
"Absolutely, I am sending everything right now: photos, comps, repair estimate. Take a look and let me know by [DATE] because I have other buyers asking about it."
[Send immediately. Follow up the next day.]

[If they say NOT FOR ME:]
"No worries at all. Can I ask what you are looking for right now? Areas, price range, property type? I want to send you deals that actually fit."
[Update their buyer profile in the app. Every no makes your buyers list smarter.]

[If they GHOST after showing interest:]
Follow up once: "Hi [NAME], just checking if you had a chance to look at [ADDRESS]. I need to move on it by [DATE]. Still interested?"
[If no response, move to the next buyer. Do not chase.]

CLOSING A BUYER:
When they say yes: "Perfect. I will send the assignment agreement now. Once you sign and send the deposit, the deal is yours. The title company will reach out about closing. Congratulations, this is a good one."
[Log the buyer commitment in the app immediately.]""",
    },
    {
        "id": "objection_price",
        "title": "Objection: Price Too Low",
        "stages": ["offer", "negotiation"],
        "goal": "Keep the conversation alive when they say your offer is too low.",
        "body": """[Stay calm. This is the most common objection. It means they are engaged, not done.]

"I understand, [NAME]. Can I ask: what number were you hoping to get?"

[Listen. Repeat their number back: "Okay, so $[THEIR NUMBER]. Got it."]

"Can I walk you through something? If you listed it with an agent at $[THEIR NUMBER], let us do the real math together:
- Agent commission, about 6 percent: that is $[X]
- Closing costs: another $[X]
- Then the months of mortgage, insurance, and taxes while you wait for a buyer: $[X] per month

So what would you actually walk away with? A lot of sellers are surprised when they run those numbers."

[Pause. Let them think.]

"Here is what my offer gives you instead: $[YOUR OFFER] cash, no commissions, no fees, no repairs, no showings with strangers walking through, no waiting on bank approvals. And we close on your timeline."

[Then ask:]
"Is the price the only thing holding this up, or is there something else going on? Because if we can get closer on the number, are you ready to move forward?"

[If they move a little:]
Meet in the middle only if it is still at or below your maximum offer. Never go above your max.

[If they will not budge:]
"I respect that. My offer stands at $[YOUR OFFER]. If anything changes, I am here. Can I follow up with you in a couple weeks?\"""",
    },
    {
        "id": "objection_just_looking",
        "title": "Objection: Just Looking / Not Sure About Selling",
        "stages": ["contacted", "appointment", "negotiation"],
        "goal": "Turn a maybe into a clear next step without pressure.",
        "body": """[This person is curious but not committed. Your job is to find out how real the interest is.]

"That is completely fine, [NAME]. Most people I talk to are just exploring their options at first."

"Can I ask you straight: on a scale of 1 to 10, how serious are you about selling in the next few months? 1 means not at all, 10 means let us get it done."

[Pause and listen to the number.]

[If 6 OR HIGHER:]
"Okay, so there is some real interest there. What would need to happen to get that to an 8 or 9? Usually it comes down to either the number or the timing. Which one is it for you?"
[Address whichever one they name.]

[If 5 OR LOWER:]
"I appreciate the honesty, truly. Here is what I suggest: let me give you my number, and I will check back in [TIMEFRAME]. If your situation changes, you already know someone who buys as is with no hassle. Fair enough?"

[Either way, end with:]
"Is it okay if I follow up with you then?\"""",
    },
    {
        "id": "objection_spouse",
        "title": "Objection: Need Spouse / Partner Approval",
        "stages": ["offer", "negotiation"],
        "goal": "Get both decision makers in the same conversation.",
        "body": """[Never try to go around the spouse. Get them together. Secondhand explanations kill deals.]

"Of course, [NAME]. That is a big decision and you should both be comfortable with it."

"Here is what usually works best: instead of you trying to explain my whole offer secondhand, can we get [SPOUSE NAME] on the phone together for five minutes? I will walk through the numbers once, answer any questions from both of you, and then you two can talk it over with the full picture. Would tonight or tomorrow evening work for a quick call together?"

[If they resist:]
"I get it. Then let me ask you honestly: if your [husband / wife / partner] was on board, is this something YOU would want to do? I just want to know where you personally stand."

[If yes:]
"Good. Then let us get them looped in so you are deciding together with all the facts. What time works for a quick three way call?"

[If they say MY SPOUSE WILL SAY NO:]
"What do you think their concern would be? The price, or just selling in general? If I can address that concern, would you be open to all of us talking?"
[Sometimes the spouse is an excuse. Sometimes it is real. Find out which.]""",
    },
    {
        "id": "objection_timeline",
        "title": "Objection: Bad Timing / Need More Time",
        "stages": ["contacted", "appointment", "negotiation"],
        "goal": "Pin down the real timeline and stay in the picture.",
        "body": """[Do not fight their timeline. Join it. Then own the follow up.]

"No rush at all, [NAME]. I would rather do this on your timeline than push you into something."

"Can I ask: when you picture this happening, what month are we talking about?"

[Whatever they say, write it down.]

"Okay, [MONTH]. Here is what I can do: I will put you in my calendar to check back [two weeks before their month]. That way this is not hanging over you, and when the time is right we can move fast."

"One question so I am ready when we talk next: is there anything about the property I should know now? Repairs it needs, tenants in place, anything like that? It helps me come back with a real number instead of starting from scratch."

"And just so I do not lose you: is [PHONE] still the best number?"

[Log the follow up date in the app. Set a reminder. Then actually follow up. Most wholesalers never follow up, which is why the ones who do get the deals.]""",
    },
]


def scripts_for_stage(stage: str) -> list[dict]:
    return [s for s in SCRIPTS if stage in s["stages"]]


def get_script(script_id: str) -> dict | None:
    for s in SCRIPTS:
        if s["id"] == script_id:
            return s
    return None
