import json
from typing import Literal

import anthropic
from pydantic import BaseModel

from config import settings

client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

SYSTEM_PROMPT = """You are an expert in the European used-car market with deep knowledge of pricing across all makes, models, and conditions.

When given a car description, you must return a JSON object with this exact structure:
{
  "status": "estimated" | "insufficient_info",
  "low_price": <float or null>,
  "high_price": <float or null>,
  "currency": "<ISO currency code, e.g. EUR, GBP> or null",
  "reasoning": "<brief explanation of your pricing logic>",
  "clarifying_question": "<single question to ask the seller> or null"
}

Rules:
- Only return an estimate if you are 100% certain of the exact price the car will sell for. Any uncertainty whatsoever about make, model, year, mileage, condition, region, options, paint, accident history, or any other factor that could affect price means you must NOT estimate.
- If you cannot be 100% certain of the exact price, set status to "insufficient_info", set prices and currency to null, and provide a single clarifying_question asking for whatever detail would resolve your uncertainty.
- When in doubt, always ask for more info rather than guessing — a wrong estimate is far worse than a clarifying question.
- The price range should reflect realistic market values — not the asking price.
- Return only the JSON object, no extra text."""


class PricerResult(BaseModel):
    status: Literal["estimated", "insufficient_info"]
    low_price: float | None
    high_price: float | None
    currency: str | None
    reasoning: str
    clarifying_question: str | None
    raw_response: str = ""


def estimate_price(description: str) -> PricerResult:
    response = client.messages.create(
        model=settings.ANTHROPIC_MODEL,
        max_tokens=512,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": description}],
    )

    raw = response.content[0].text
    clean = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    data = json.loads(clean)
    result = PricerResult.model_validate(data)
    result.raw_response = raw
    return result
