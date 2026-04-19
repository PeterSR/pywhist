from dataclasses import dataclass

from ..cards import Card
from .bids import Call


class BaseAction:
    """Base class for game actions."""


@dataclass(frozen=True)
class PlayAction(BaseAction):
    card: Card

    def __str__(self) -> str:
        return f"Played {self.card.symbol}"


@dataclass(frozen=True)
class CallAction(BaseAction):
    call: Call

    def __str__(self) -> str:
        return f"Called {self.call.trump.symbol} trump with {self.call.partner_ace.symbol} ace"
