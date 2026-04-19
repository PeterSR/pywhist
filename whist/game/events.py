from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from ..cards import Card, Trick
from .actions import BaseAction, action_from_dict
from .bids import Bid, bid_from_dict, bid_to_dict
from .partners import TeamID
from .phase import Phase
from .player import Player


class BaseEvent:
    def to_dict(self) -> dict[str, Any]:
        raise NotImplementedError


# ---- play-phase events ---------------------------------------------------


@dataclass(frozen=True)
class ActionTakenEvent(BaseEvent):
    player: Player
    action: BaseAction

    def __str__(self) -> str:
        return f"Player {self.player.name}: {self.action}"

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": "action_taken",
            "player": self.player.to_dict(),
            "action": self.action.to_dict(),
        }

    @classmethod
    def from_dict(cls, d: Mapping[str, Any]) -> ActionTakenEvent:
        return cls(
            player=Player.from_dict(d["player"]),
            action=action_from_dict(d["action"]),
        )


@dataclass(frozen=True)
class TrickTakenEvent(BaseEvent):
    player: Player
    team_id: TeamID
    trick: Trick

    def __str__(self) -> str:
        trick_symbols = tuple(card.symbol for card in self.trick)
        return f"Player {self.player.name} took {trick_symbols}"

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": "trick_taken",
            "player": self.player.to_dict(),
            "team_id": int(self.team_id),
            "trick": [c.to_dict() for c in self.trick],
        }

    @classmethod
    def from_dict(cls, d: Mapping[str, Any]) -> TrickTakenEvent:
        cards_list = [Card.from_dict(c) for c in d["trick"]]
        if len(cards_list) != 4:
            raise ValueError(f"Expected 4 cards in trick, got {len(cards_list)}")
        trick: Trick = (cards_list[0], cards_list[1], cards_list[2], cards_list[3])
        return cls(
            player=Player.from_dict(d["player"]),
            team_id=TeamID(int(d["team_id"])),
            trick=trick,
        )


@dataclass(frozen=True)
class PhaseTransitionEvent(BaseEvent):
    from_phase: Phase
    to_phase: Phase

    def __str__(self) -> str:
        return f"Phase: {self.from_phase.value} → {self.to_phase.value}"

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": "phase_transition",
            "from_phase": self.from_phase.value,
            "to_phase": self.to_phase.value,
        }

    @classmethod
    def from_dict(cls, d: Mapping[str, Any]) -> PhaseTransitionEvent:
        return cls(
            from_phase=Phase(d["from_phase"]),
            to_phase=Phase(d["to_phase"]),
        )


# ---- deal / auction events -----------------------------------------------


@dataclass(frozen=True)
class DealEvent(BaseEvent):
    """Emitted at the moment cards are dealt. Records the rng seed so a hand
    is reconstructible from `(seed, action_sequence)`.
    """

    dealer: Player
    seed: int | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": "deal",
            "dealer": self.dealer.to_dict(),
            "seed": self.seed,
        }

    @classmethod
    def from_dict(cls, d: Mapping[str, Any]) -> DealEvent:
        seed = d.get("seed")
        return cls(
            dealer=Player.from_dict(d["dealer"]),
            seed=int(seed) if seed is not None else None,
        )


@dataclass(frozen=True)
class AuctionMoveEvent(BaseEvent):
    """Any move during the auction — bid, pass, det-kan-jeg-selv, gå-med.

    A tagged union (via `kind`) keeps the wire surface compact. `bid` is
    populated for kind='bid' and the klør-rewritten form for kind='bid' when
    the reducer rewrote it.
    """

    player: Player
    kind: str  # "bid" | "pass" | "det_kan_jeg_selv" | "gaa_med"
    bid: Bid | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": "auction_move",
            "player": self.player.to_dict(),
            "kind": self.kind,
            "bid": bid_to_dict(self.bid) if self.bid is not None else None,
        }

    @classmethod
    def from_dict(cls, d: Mapping[str, Any]) -> AuctionMoveEvent:
        bid_d = d.get("bid")
        return cls(
            player=Player.from_dict(d["player"]),
            kind=str(d["kind"]),
            bid=bid_from_dict(bid_d) if bid_d is not None else None,
        )


@dataclass(frozen=True)
class AuctionBounceEvent(BaseEvent):
    """Turn bounced back to a previous non-passed bidder after an overcall."""

    from_player: Player
    to_player: Player

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": "auction_bounce",
            "from_player": self.from_player.to_dict(),
            "to_player": self.to_player.to_dict(),
        }

    @classmethod
    def from_dict(cls, d: Mapping[str, Any]) -> AuctionBounceEvent:
        return cls(
            from_player=Player.from_dict(d["from_player"]),
            to_player=Player.from_dict(d["to_player"]),
        )


@dataclass(frozen=True)
class BidWonEvent(BaseEvent):
    winner: Player
    bid: Bid

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": "bid_won",
            "winner": self.winner.to_dict(),
            "bid": bid_to_dict(self.bid),
        }

    @classmethod
    def from_dict(cls, d: Mapping[str, Any]) -> BidWonEvent:
        return cls(winner=Player.from_dict(d["winner"]), bid=bid_from_dict(d["bid"]))


@dataclass(frozen=True)
class RedealEvent(BaseEvent):
    """Emitted on all-pass or jernhaand declaration — next dealer advances."""

    reason: str  # "all_pass" | "jernhaand"
    new_dealer: Player

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": "redeal",
            "reason": self.reason,
            "new_dealer": self.new_dealer.to_dict(),
        }

    @classmethod
    def from_dict(cls, d: Mapping[str, Any]) -> RedealEvent:
        return cls(reason=str(d["reason"]), new_dealer=Player.from_dict(d["new_dealer"]))


@dataclass(frozen=True)
class BanketEvent(BaseEvent):
    player: Player

    def to_dict(self) -> dict[str, Any]:
        return {"type": "banket_emitted", "player": self.player.to_dict()}

    @classmethod
    def from_dict(cls, d: Mapping[str, Any]) -> BanketEvent:
        return cls(player=Player.from_dict(d["player"]))


@dataclass(frozen=True)
class ReBanketEvent(BaseEvent):
    player: Player

    def to_dict(self) -> dict[str, Any]:
        return {"type": "re_banket_emitted", "player": self.player.to_dict()}

    @classmethod
    def from_dict(cls, d: Mapping[str, Any]) -> ReBanketEvent:
        return cls(player=Player.from_dict(d["player"]))


@dataclass(frozen=True)
class JernhaandOptionEvent(BaseEvent):
    """Emitted right after dealing when one or more players have jernhaand."""

    eligible: tuple[Player, ...]

    def to_dict(self) -> dict[str, Any]:
        return {"type": "jernhaand_option", "eligible": [p.to_dict() for p in self.eligible]}

    @classmethod
    def from_dict(cls, d: Mapping[str, Any]) -> JernhaandOptionEvent:
        return cls(eligible=tuple(Player.from_dict(p) for p in d["eligible"]))


@dataclass(frozen=True)
class JernhaandDeclaredEvent(BaseEvent):
    player: Player

    def to_dict(self) -> dict[str, Any]:
        return {"type": "jernhaand_declared", "player": self.player.to_dict()}

    @classmethod
    def from_dict(cls, d: Mapping[str, Any]) -> JernhaandDeclaredEvent:
        return cls(player=Player.from_dict(d["player"]))


@dataclass(frozen=True)
class KingCalledEvent(BaseEvent):
    """Declarer called a king (all-4-aces path)."""

    declarer: Player
    trump: str
    king_suit: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": "king_called",
            "declarer": self.declarer.to_dict(),
            "trump": self.trump,
            "king_suit": self.king_suit,
        }

    @classmethod
    def from_dict(cls, d: Mapping[str, Any]) -> KingCalledEvent:
        return cls(
            declarer=Player.from_dict(d["declarer"]),
            trump=str(d["trump"]),
            king_suit=str(d["king_suit"]),
        )


# ---- dispatch ------------------------------------------------------------

_EVENT_TAGS: dict[str, type[BaseEvent]] = {
    "action_taken": ActionTakenEvent,
    "trick_taken": TrickTakenEvent,
    "phase_transition": PhaseTransitionEvent,
    "deal": DealEvent,
    "auction_move": AuctionMoveEvent,
    "auction_bounce": AuctionBounceEvent,
    "bid_won": BidWonEvent,
    "redeal": RedealEvent,
    "banket_emitted": BanketEvent,
    "re_banket_emitted": ReBanketEvent,
    "jernhaand_option": JernhaandOptionEvent,
    "jernhaand_declared": JernhaandDeclaredEvent,
    "king_called": KingCalledEvent,
}


def event_from_dict(d: Mapping[str, Any]) -> BaseEvent:
    tag = d["type"]
    cls = _EVENT_TAGS.get(tag)
    if cls is None:
        raise ValueError(f"Unknown event tag: {tag!r}")
    return cls.from_dict(d)  # type: ignore[attr-defined,no-any-return]
