import json
from typing import Literal, TYPE_CHECKING

import anthropic
from pydantic import BaseModel

from agents.pricer import PricerResult
from config import settings

if TYPE_CHECKING:
    from conversation import ConversationState

client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

OPENING_SYSTEM_PROMPT = """You are a skilled but friendly car buyer negotiating with a private seller.

You will be given:
- The car description as posted by the seller
- An internal price estimate (low and high) that you must NOT reveal

Write a single opening message to the seller. The message must:
- Acknowledge the car naturally, as if you read their listing
- Open with an offer price that is below the low end of the estimate
- Be conversational and polite, never aggressive
- Be written in the same language as the car description
- Contain only the message text — no preamble, no explanation"""


CONTINUE_SYSTEM_PROMPT = """You are a skilled but friendly car buyer in an ongoing negotiation with a private seller.

You will be given:
- The car description
- Your internal price estimate (low and high) — never reveal this to the seller
- The full transcript of the negotiation so far (your prior messages and the seller's replies)
- The seller's latest message

Negotiation rules:
- Stay consistent with your prior offers in the transcript. Do not contradict yourself.
- Walk your offer up gradually only when justified by the seller's pushback.
- The HIGH end of the internal estimate is a HARD CEILING. Never offer at or above it. If the seller refuses to come below it, walk away.
- Be conversational and polite, never aggressive.
- Always reply in the same language as the seller.

You must decide the negotiation's status:
- "negotiating" — the deal is still being worked out, send another message
- "deal_agreed" — the seller has accepted a price within your range and the deal is effectively closed
- "walk_away" — the seller will not come below the hard ceiling, or the deal has clearly stalled

Return a JSON object with this exact shape:
{
  "message": "<your reply to the seller, in their language>",
  "status": "negotiating" | "deal_agreed" | "walk_away"
}

Return ONLY the JSON object, no extra text."""


class NegotiationTurn(BaseModel):
    message: str
    status: Literal["negotiating", "deal_agreed", "walk_away"]


def write_opening_message(description: str, estimate: PricerResult) -> str:
    user_content = (
        f"Car description:\n{description}\n\n"
        f"Internal estimate: {estimate.currency} {estimate.low_price} – {estimate.high_price}\n\n"
        "Write the opening negotiation message now."
    )

    response = client.messages.create(
        model=settings.ANTHROPIC_MODEL,
        max_tokens=256,
        system=OPENING_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_content}],
    )

    return response.content[0].text.strip()


def continue_negotiation(state: "ConversationState", seller_message: str) -> NegotiationTurn:
    transcript_lines = [f"{turn.speaker.upper()}: {turn.text}" for turn in state.history]
    transcript = "\n".join(transcript_lines) if transcript_lines else "(no prior turns)"

    estimate = state.estimate
    user_content = (
        f"Car description:\n{state.description}\n\n"
        f"Internal estimate (HARD CEILING = high): "
        f"{estimate.currency} {estimate.low_price} – {estimate.high_price}\n\n"
        f"Transcript so far:\n{transcript}\n\n"
        f"Seller's latest message:\n{seller_message}\n\n"
        "Return the JSON object now."
    )

    response = client.messages.create(
        model=settings.ANTHROPIC_MODEL,
        max_tokens=512,
        system=CONTINUE_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_content}],
    )

    raw = response.content[0].text
    clean = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    data = json.loads(clean)
    return NegotiationTurn.model_validate(data)
