"""Bidding types — bid ladder, rank, and the klør-almindelig auto-rewrite.

The legacy `Call` type is kept here because `CallAction` still drives the
post-auction trump + partner-ace selection (see `phase.Phase.CALLING`).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from ..cards import Suit
from .ruleset import BidModifier, NoloContract

# ---- bid kinds ------------------------------------------------------------


@dataclass(frozen=True)
class NumberBid:
    level: int  # 7..13
    modifier: BidModifier

    def to_dict(self) -> dict[str, Any]:
        return {"kind": "number", "level": self.level, "modifier": self.modifier.value}

    @classmethod
    def from_dict(cls, d: Mapping[str, Any]) -> NumberBid:
        return cls(level=int(d["level"]), modifier=BidModifier(d["modifier"]))


@dataclass(frozen=True)
class NoloBid:
    contract: NoloContract

    def to_dict(self) -> dict[str, Any]:
        return {"kind": "nolo", "contract": self.contract.value}

    @classmethod
    def from_dict(cls, d: Mapping[str, Any]) -> NoloBid:
        return cls(contract=NoloContract(d["contract"]))


Bid = NumberBid | NoloBid


def bid_from_dict(d: Mapping[str, Any]) -> Bid:
    kind = d["kind"]
    if kind == "number":
        return NumberBid.from_dict(d)
    if kind == "nolo":
        return NoloBid.from_dict(d)
    raise ValueError(f"Unknown bid kind: {kind!r}")


def bid_to_dict(b: Bid) -> dict[str, Any]:
    return b.to_dict()


# ---- bid ladder -----------------------------------------------------------

_MODIFIER_ORDER: tuple[BidModifier, ...] = (
    BidModifier.ALMINDELIG,
    BidModifier.GODE,
    BidModifier.HALVE,
    BidModifier.VIP,
    BidModifier.SANS,
)

# Nolo contracts are inserted AFTER level N's modifier group — Sol after 9,
# Ren Sol after 10, Bordlægger after 11, Ren Bordlægger after 12.
_NOLO_INSERT_AFTER: dict[int, NoloContract] = {
    9: NoloContract.SOL,
    10: NoloContract.REN_SOL,
    11: NoloContract.BORDLAEGGER,
    12: NoloContract.REN_BORDLAEGGER,
}


def _build_ladder() -> tuple[Bid, ...]:
    ladder: list[Bid] = []
    for level in range(7, 14):
        for modifier in _MODIFIER_ORDER:
            ladder.append(NumberBid(level=level, modifier=modifier))
        if level in _NOLO_INSERT_AFTER:
            ladder.append(NoloBid(contract=_NOLO_INSERT_AFTER[level]))
    return tuple(ladder)


BID_LADDER: tuple[Bid, ...] = _build_ladder()

_BID_RANK: dict[Bid, int] = {b: i for i, b in enumerate(BID_LADDER)}


def bid_rank(b: Bid) -> int:
    """Return the ladder index of `b`; higher = stronger bid."""
    try:
        return _BID_RANK[b]
    except KeyError as exc:
        raise ValueError(f"Bid not in BID_LADDER: {b!r}") from exc


# ---- klør auto-rewrite ----------------------------------------------------


def rewrite_klor_almindelig(b: Bid, trump: Suit | None) -> Bid:
    """Spec §3.2.1: klør-trumf under *almindelig* is auto-rewritten to *gode*.

    Invoked at bid-submission time. `trump` is the trump the bidder *would*
    announce — for Almindelig the bidder must declare it up front (they pick
    trump + partner-ace immediately), so this can be applied at the reducer
    entry point. For all other bid kinds, this is a no-op.
    """
    if isinstance(b, NumberBid) and b.modifier == BidModifier.ALMINDELIG and trump == Suit.Club:
        return NumberBid(level=b.level, modifier=BidModifier.GODE)
    return b


# ---- legacy `Call` (still used by the CALLING phase) ---------------------


@dataclass
class Call:
    trump: Suit = None  # type: ignore[assignment]
    partner_ace: Suit = None  # type: ignore[assignment]

    def to_dict(self) -> dict[str, Any]:
        trump = self.trump if self.trump is not None else Suit.Unknown
        partner_ace = self.partner_ace if self.partner_ace is not None else Suit.Unknown
        return {"trump": trump.code, "partner_ace": partner_ace.code}

    @classmethod
    def from_dict(cls, d: Mapping[str, Any]) -> Call:
        return cls(
            trump=Suit.from_code(d["trump"]),
            partner_ace=Suit.from_code(d["partner_ace"]),
        )


__all__ = [
    "BID_LADDER",
    "Bid",
    "BidModifier",
    "Call",
    "NoloBid",
    "NoloContract",
    "NumberBid",
    "bid_from_dict",
    "bid_rank",
    "bid_to_dict",
    "rewrite_klor_almindelig",
]
