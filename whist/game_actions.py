from dataclasses import dataclass

from .cards import Card
from .game_bids import Bid, Call


class BaseAction:
    """
    Base class for game actions
    """


@dataclass(frozen=True)
class PlayAction(BaseAction):
    card: Card

    def __str__(self):
        return f"Played {self.card.symbol}"


@dataclass(frozen=True)
class BidAction(BaseAction):
    bid: Bid

    def __str__(self):
        return f"Bid {self.bid}"


@dataclass(frozen=True)
class CallAction(BaseAction):
    call: Call

    def __str__(self):
        return f"Called {self.call.trump.symbol} with {self.call.partner_ace.symbol} ace"