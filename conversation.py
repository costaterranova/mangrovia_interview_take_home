from dataclasses import dataclass, field
from typing import Literal

from agents.pricer import PricerResult


Phase = Literal["idle", "awaiting_info", "negotiating"]


@dataclass
class Turn:
    speaker: Literal["seller", "buyer"]
    text: str


@dataclass
class ConversationState:
    phase: Phase = "idle"
    description: str = ""
    estimate: PricerResult | None = None
    history: list[Turn] = field(default_factory=list)
    estimate_id: int | None = None


state = ConversationState()


def reset() -> None:
    state.phase = "idle"
    state.description = ""
    state.estimate = None
    state.history = []
    state.estimate_id = None
