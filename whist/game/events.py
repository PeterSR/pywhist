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
class KattenExchangedEvent(BaseEvent):
    player: Player
    took_count: int  # 0 or 3
    # Discards are not exposed publicly — the dict only carries the count.
    discards_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": "katten_exchanged",
            "player": self.player.to_dict(),
            "took_count": self.took_count,
            "discards_count": self.discards_count,
        }

    @classmethod
    def from_dict(cls, d: Mapping[str, Any]) -> KattenExchangedEvent:
        return cls(
            player=Player.from_dict(d["player"]),
            took_count=int(d["took_count"]),
            discards_count=int(d.get("discards_count", 0)),
        )


@dataclass(frozen=True)
class VipFlipEvent(BaseEvent):
    index: int  # 0-based flip position
    card: Card

    def to_dict(self) -> dict[str, Any]:
        return {"type": "vip_flip_done", "index": self.index, "card": self.card.to_dict()}

    @classmethod
    def from_dict(cls, d: Mapping[str, Any]) -> VipFlipEvent:
        return cls(index=int(d["index"]), card=Card.from_dict(d["card"]))


@dataclass(frozen=True)
class VipStoppedEvent(BaseEvent):
    final_trump: str  # Suit code, or "_" for sans
    flip_count: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": "vip_stopped",
            "final_trump": self.final_trump,
            "flip_count": self.flip_count,
        }

    @classmethod
    def from_dict(cls, d: Mapping[str, Any]) -> VipStoppedEvent:
        return cls(final_trump=str(d["final_trump"]), flip_count=int(d["flip_count"]))


@dataclass(frozen=True)
class VipTakeoverEvent(BaseEvent):
    """A gå-med player has accepted the current Vip trump and replaced declarer."""

    new_declarer: Player
    trump: str  # Suit code, or "_" for sans

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": "vip_takeover",
            "new_declarer": self.new_declarer.to_dict(),
            "trump": self.trump,
        }

    @classmethod
    def from_dict(cls, d: Mapping[str, Any]) -> VipTakeoverEvent:
        return cls(
            new_declarer=Player.from_dict(d["new_declarer"]),
            trump=str(d["trump"]),
        )


@dataclass(frozen=True)
class HalveTrumpChosenEvent(BaseEvent):
    partner: Player
    trump: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": "halve_trump_chosen",
            "partner": self.partner.to_dict(),
            "trump": self.trump,
        }

    @classmethod
    def from_dict(cls, d: Mapping[str, Any]) -> HalveTrumpChosenEvent:
        return cls(partner=Player.from_dict(d["partner"]), trump=str(d["trump"]))


@dataclass(frozen=True)
class MarkerPlacedEvent(BaseEvent):
    player: Player
    claimed_suit: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": "marker_placed",
            "player": self.player.to_dict(),
            "claimed_suit": self.claimed_suit,
        }

    @classmethod
    def from_dict(cls, d: Mapping[str, Any]) -> MarkerPlacedEvent:
        return cls(
            player=Player.from_dict(d["player"]),
            claimed_suit=str(d["claimed_suit"]),
        )


@dataclass(frozen=True)
class PartnerRevealedEvent(BaseEvent):
    declarer: Player
    partner: Player

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": "partner_revealed",
            "declarer": self.declarer.to_dict(),
            "partner": self.partner.to_dict(),
        }

    @classmethod
    def from_dict(cls, d: Mapping[str, Any]) -> PartnerRevealedEvent:
        return cls(
            declarer=Player.from_dict(d["declarer"]),
            partner=Player.from_dict(d["partner"]),
        )


@dataclass(frozen=True)
class ScoreEvent(BaseEvent):
    per_player: dict[int, int]  # player_id -> score delta

    def to_dict(self) -> dict[str, Any]:
        return {"type": "score", "per_player": {str(k): int(v) for k, v in self.per_player.items()}}

    @classmethod
    def from_dict(cls, d: Mapping[str, Any]) -> ScoreEvent:
        return cls(per_player={int(k): int(v) for k, v in d["per_player"].items()})


@dataclass(frozen=True)
class CapsizeEvent(BaseEvent):
    """Nolo declarer took too many tricks — contract busted."""

    declarer: Player
    tricks_taken: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": "capsize",
            "declarer": self.declarer.to_dict(),
            "tricks_taken": self.tricks_taken,
        }

    @classmethod
    def from_dict(cls, d: Mapping[str, Any]) -> CapsizeEvent:
        return cls(
            declarer=Player.from_dict(d["declarer"]),
            tricks_taken=int(d["tricks_taken"]),
        )


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


# ---- bid whist events ----------------------------------------------------


@dataclass(frozen=True)
class BidWhistBidMadeEvent(BaseEvent):
    player: Player
    level: int
    trump: str | None  # suit code, or None for no-trump

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": "bid_whist_bid_made",
            "player": self.player.to_dict(),
            "level": self.level,
            "trump": self.trump,
        }

    @classmethod
    def from_dict(cls, d: Mapping[str, Any]) -> BidWhistBidMadeEvent:
        return cls(
            player=Player.from_dict(d["player"]),
            level=int(d["level"]),
            trump=d.get("trump"),
        )


@dataclass(frozen=True)
class BidWhistBidWonEvent(BaseEvent):
    winner: Player
    level: int
    trump: str | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": "bid_whist_bid_won",
            "winner": self.winner.to_dict(),
            "level": self.level,
            "trump": self.trump,
        }

    @classmethod
    def from_dict(cls, d: Mapping[str, Any]) -> BidWhistBidWonEvent:
        return cls(
            winner=Player.from_dict(d["winner"]),
            level=int(d["level"]),
            trump=d.get("trump"),
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
    "katten_exchanged": KattenExchangedEvent,
    "vip_flip_done": VipFlipEvent,
    "vip_stopped": VipStoppedEvent,
    "vip_takeover": VipTakeoverEvent,
    "halve_trump_chosen": HalveTrumpChosenEvent,
    "marker_placed": MarkerPlacedEvent,
    "partner_revealed": PartnerRevealedEvent,
    "score": ScoreEvent,
    "capsize": CapsizeEvent,
    "bid_whist_bid_made": BidWhistBidMadeEvent,
    "bid_whist_bid_won": BidWhistBidWonEvent,
}


def event_from_dict(d: Mapping[str, Any]) -> BaseEvent:
    tag = d["type"]
    cls = _EVENT_TAGS.get(tag)
    if cls is None:
        raise ValueError(f"Unknown event tag: {tag!r}")
    return cls.from_dict(d)  # type: ignore[attr-defined,no-any-return]
