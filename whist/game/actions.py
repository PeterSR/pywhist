from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from ..cards import Card, Suit
from .bids import Bid, Call, bid_from_dict, bid_to_dict
from .player import Player


class BaseAction:
    """Base class for game actions."""

    def to_dict(self) -> dict[str, Any]:
        raise NotImplementedError


# ---- play phase ----------------------------------------------------------


@dataclass(frozen=True)
class PlayAction(BaseAction):
    card: Card

    def __str__(self) -> str:
        return f"Played {self.card.symbol}"

    def to_dict(self) -> dict[str, Any]:
        return {"type": "play", "card": self.card.to_dict()}

    @classmethod
    def from_dict(cls, d: Mapping[str, Any]) -> PlayAction:
        return cls(Card.from_dict(d["card"]))


# ---- post-auction trump + partner-ace naming ------------------------------


@dataclass(frozen=True)
class CallAction(BaseAction):
    call: Call

    def __str__(self) -> str:
        return f"Called {self.call.trump.symbol} trump with {self.call.partner_ace.symbol} ace"

    def to_dict(self) -> dict[str, Any]:
        return {"type": "call", "call": self.call.to_dict()}

    @classmethod
    def from_dict(cls, d: Mapping[str, Any]) -> CallAction:
        return cls(Call.from_dict(d["call"]))


@dataclass(frozen=True)
class KingCallAction(BaseAction):
    """Post-auction trump + king-partner naming when declarer holds all 4 aces.

    The `king_suit` is the suit of the king being called as partner. Must not
    equal the named trump suit (same constraint as partner-ace vs trump).
    """

    trump: Suit
    king_suit: Suit

    def __str__(self) -> str:
        return f"Called {self.trump.symbol} trump with {self.king_suit.symbol} king"

    def to_dict(self) -> dict[str, Any]:
        return {"type": "king_call", "trump": self.trump.code, "king_suit": self.king_suit.code}

    @classmethod
    def from_dict(cls, d: Mapping[str, Any]) -> KingCallAction:
        return cls(trump=Suit.from_code(d["trump"]), king_suit=Suit.from_code(d["king_suit"]))


# ---- auction phase --------------------------------------------------------


@dataclass(frozen=True)
class BidAction(BaseAction):
    bid: Bid
    # Trump is only needed up-front for almindelig (to trigger klør-rewrite);
    # for other bid kinds trump is determined later. `None` means
    # "unspecified" at bid time.
    trump: Suit | None = None

    def __str__(self) -> str:
        trump_str = f" (trump {self.trump.symbol})" if self.trump is not None else ""
        return f"Bid {self.bid}{trump_str}"

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": "bid",
            "bid": bid_to_dict(self.bid),
            "trump": self.trump.code if self.trump is not None else None,
        }

    @classmethod
    def from_dict(cls, d: Mapping[str, Any]) -> BidAction:
        trump_code = d.get("trump")
        return cls(
            bid=bid_from_dict(d["bid"]),
            trump=Suit.from_code(trump_code) if trump_code is not None else None,
        )


@dataclass(frozen=True)
class PassAction(BaseAction):
    def __str__(self) -> str:
        return "Pass"

    def to_dict(self) -> dict[str, Any]:
        return {"type": "pass"}

    @classmethod
    def from_dict(cls, _d: Mapping[str, Any]) -> PassAction:
        return cls()


@dataclass(frozen=True)
class DetKanJegSelvAction(BaseAction):
    """'I can do that myself' — claim the overcaller's bid as your own.

    Legal only for the player whose bid was just overcalled; the reducer
    validates this.
    """

    def __str__(self) -> str:
        return "Det kan jeg selv"

    def to_dict(self) -> dict[str, Any]:
        return {"type": "det_kan_jeg_selv"}

    @classmethod
    def from_dict(cls, _d: Mapping[str, Any]) -> DetKanJegSelvAction:
        return cls()


@dataclass(frozen=True)
class GaaMedAction(BaseAction):
    """'Go along' — join a Vip or nolo contract without overcalling.

    Spec §3.3.1. Once you gå med, you forfeit any further overcalling.
    """

    def __str__(self) -> str:
        return "Gå med"

    def to_dict(self) -> dict[str, Any]:
        return {"type": "gaa_med"}

    @classmethod
    def from_dict(cls, _d: Mapping[str, Any]) -> GaaMedAction:
        return cls()


# ---- banket phase ---------------------------------------------------------


@dataclass(frozen=True)
class BanketAction(BaseAction):
    """Opponent doubles the contract (x2)."""

    def to_dict(self) -> dict[str, Any]:
        return {"type": "banket"}

    @classmethod
    def from_dict(cls, _d: Mapping[str, Any]) -> BanketAction:
        return cls()


@dataclass(frozen=True)
class ReBanketAction(BaseAction):
    """Declarer (or partner) counter-doubles (x4)."""

    def to_dict(self) -> dict[str, Any]:
        return {"type": "re_banket"}

    @classmethod
    def from_dict(cls, _d: Mapping[str, Any]) -> ReBanketAction:
        return cls()


@dataclass(frozen=True)
class BanketSkipAction(BaseAction):
    """Decline to banket — proceed without doubling."""

    def to_dict(self) -> dict[str, Any]:
        return {"type": "banket_skip"}

    @classmethod
    def from_dict(cls, _d: Mapping[str, Any]) -> BanketSkipAction:
        return cls()


# ---- jernhånd -------------------------------------------------------------


@dataclass(frozen=True)
class JernhaandAction(BaseAction):
    """Declare jernhaand — force redeal with dealer rotation."""

    player: Player

    def to_dict(self) -> dict[str, Any]:
        return {"type": "jernhaand", "player": self.player.to_dict()}

    @classmethod
    def from_dict(cls, d: Mapping[str, Any]) -> JernhaandAction:
        return cls(player=Player.from_dict(d["player"]))


@dataclass(frozen=True)
class JernhaandDeclineAction(BaseAction):
    """Decline jernhaand — proceed to bidding."""

    player: Player

    def to_dict(self) -> dict[str, Any]:
        return {"type": "jernhaand_decline", "player": self.player.to_dict()}

    @classmethod
    def from_dict(cls, d: Mapping[str, Any]) -> JernhaandDeclineAction:
        return cls(player=Player.from_dict(d["player"]))


# ---- sub-phase actions ---------------------------------------------------


@dataclass(frozen=True)
class KattenExchangeTakeAction(BaseAction):
    """Exchanger takes all 3 katten cards (must follow with discards)."""

    def to_dict(self) -> dict[str, Any]:
        return {"type": "katten_take"}

    @classmethod
    def from_dict(cls, _d: Mapping[str, Any]) -> KattenExchangeTakeAction:
        return cls()


@dataclass(frozen=True)
class KattenExchangeSkipAction(BaseAction):
    """Exchanger skips the katten — takes 0 cards."""

    def to_dict(self) -> dict[str, Any]:
        return {"type": "katten_skip"}

    @classmethod
    def from_dict(cls, _d: Mapping[str, Any]) -> KattenExchangeSkipAction:
        return cls()


@dataclass(frozen=True)
class KattenDiscardAction(BaseAction):
    """Discard exactly 3 cards back after taking the katten."""

    cards: tuple[Card, Card, Card]

    def to_dict(self) -> dict[str, Any]:
        return {"type": "katten_discard", "cards": [c.to_dict() for c in self.cards]}

    @classmethod
    def from_dict(cls, d: Mapping[str, Any]) -> KattenDiscardAction:
        cards_list = [Card.from_dict(c) for c in d["cards"]]
        if len(cards_list) != 3:
            raise ValueError(f"Expected 3 cards, got {len(cards_list)}")
        return cls(cards=(cards_list[0], cards_list[1], cards_list[2]))


@dataclass(frozen=True)
class VipFlipAction(BaseAction):
    """Flip the next katten card during Vip — reveals trump candidate."""

    def to_dict(self) -> dict[str, Any]:
        return {"type": "vip_flip"}

    @classmethod
    def from_dict(cls, _d: Mapping[str, Any]) -> VipFlipAction:
        return cls()


@dataclass(frozen=True)
class VipStopAction(BaseAction):
    """Stop flipping — accept the current revealed suit as trump."""

    def to_dict(self) -> dict[str, Any]:
        return {"type": "vip_stop"}

    @classmethod
    def from_dict(cls, _d: Mapping[str, Any]) -> VipStopAction:
        return cls()


@dataclass(frozen=True)
class VipContinueAction(BaseAction):
    """Keep flipping after a gå-med player declined to take over."""

    def to_dict(self) -> dict[str, Any]:
        return {"type": "vip_continue"}

    @classmethod
    def from_dict(cls, _d: Mapping[str, Any]) -> VipContinueAction:
        return cls()


@dataclass(frozen=True)
class HalveTrumpChoiceAction(BaseAction):
    """Partner's trump choice under a Halve bid."""

    trump: Suit

    def to_dict(self) -> dict[str, Any]:
        return {"type": "halve_trump", "trump": self.trump.code}

    @classmethod
    def from_dict(cls, d: Mapping[str, Any]) -> HalveTrumpChoiceAction:
        return cls(trump=Suit.from_code(d["trump"]))


@dataclass(frozen=True)
class MarkerCardAction(BaseAction):
    """Declarer places a face-down marker card as partner-ace-suit surrogate.

    Legal only when declarer holds ≤ `marker_card_threshold` of partner-ace suit.
    """

    card: Card

    def to_dict(self) -> dict[str, Any]:
        return {"type": "marker", "card": self.card.to_dict()}

    @classmethod
    def from_dict(cls, d: Mapping[str, Any]) -> MarkerCardAction:
        return cls(card=Card.from_dict(d["card"]))


@dataclass(frozen=True)
class MarkerSkipAction(BaseAction):
    def to_dict(self) -> dict[str, Any]:
        return {"type": "marker_skip"}

    @classmethod
    def from_dict(cls, _d: Mapping[str, Any]) -> MarkerSkipAction:
        return cls()


# ---- bid whist actions ---------------------------------------------------


@dataclass(frozen=True)
class BidWhistBidAction(BaseAction):
    """Bid whist bid: a level (books above 6) + trump suit (or no-trump)."""

    level: int
    trump: Suit | None  # None → no-trump

    def __str__(self) -> str:
        trump_str = "NT" if self.trump is None else self.trump.symbol
        return f"Bid {self.level} {trump_str}"

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": "bid_whist_bid",
            "level": self.level,
            "trump": self.trump.code if self.trump is not None else None,
        }

    @classmethod
    def from_dict(cls, d: Mapping[str, Any]) -> BidWhistBidAction:
        trump_raw = d.get("trump")
        trump = Suit.from_code(trump_raw) if trump_raw is not None else None
        return cls(level=int(d["level"]), trump=trump)


# ---- dispatch -------------------------------------------------------------

_ACTION_TAGS: dict[str, type[BaseAction]] = {
    "play": PlayAction,
    "call": CallAction,
    "king_call": KingCallAction,
    "bid": BidAction,
    "pass": PassAction,
    "det_kan_jeg_selv": DetKanJegSelvAction,
    "gaa_med": GaaMedAction,
    "banket": BanketAction,
    "re_banket": ReBanketAction,
    "banket_skip": BanketSkipAction,
    "jernhaand": JernhaandAction,
    "jernhaand_decline": JernhaandDeclineAction,
    "katten_take": KattenExchangeTakeAction,
    "katten_skip": KattenExchangeSkipAction,
    "katten_discard": KattenDiscardAction,
    "vip_flip": VipFlipAction,
    "vip_stop": VipStopAction,
    "vip_continue": VipContinueAction,
    "halve_trump": HalveTrumpChoiceAction,
    "marker": MarkerCardAction,
    "marker_skip": MarkerSkipAction,
    "bid_whist_bid": BidWhistBidAction,
}


def action_from_dict(d: Mapping[str, Any]) -> BaseAction:
    tag = d["type"]
    cls = _ACTION_TAGS.get(tag)
    if cls is None:
        raise ValueError(f"Unknown action tag: {tag!r}")
    return cls.from_dict(d)  # type: ignore[attr-defined,no-any-return]
