"""Esmakker Whist scoring.

Covers base points, modifier and banket multipliers, overtrick scaling,
zero-sum settlement, and the selvmakker multiplier.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..cards import Suit
from .bids import Bid, NoloBid, NoloContract, NumberBid
from .partners import Partners
from .player import Player
from .ruleset import BidModifier, Ruleset

Score = int

_BASE_NUMBER: dict[int, int] = {7: 5, 8: 10, 9: 20, 10: 40, 11: 80, 12: 160, 13: 320}
_BASE_NOLO: dict[NoloContract, int] = {
    NoloContract.SOL: 50,
    NoloContract.REN_SOL: 100,
    NoloContract.BORDLAEGGER: 200,
    NoloContract.REN_BORDLAEGGER: 400,
}
_VIP_DOUBLE_SUITS: frozenset[Suit] = frozenset({Suit.Club, Suit.Unknown})


@dataclass(frozen=True)
class ScoringContext:
    bid: Bid
    trump: Suit
    vip_flip_count: int
    banket: bool
    re_banket: bool
    tricks_target: int
    tricks_taken_by_declarer_side: int
    ruleset: Ruleset


def base_points(bid: Bid, ruleset: Ruleset) -> int:
    if isinstance(bid, NumberBid):
        return _BASE_NUMBER[bid.level]
    if isinstance(bid, NoloBid):
        if bid.contract == NoloContract.BORDLAEGGER:
            return ruleset.bordlaegger_base_points
        if bid.contract == NoloContract.REN_BORDLAEGGER:
            return ruleset.ren_bordlaegger_base_points
        return _BASE_NOLO[bid.contract]
    raise TypeError(f"Unknown bid type: {bid!r}")


def modifier_multiplier(bid: Bid) -> int:
    if isinstance(bid, NumberBid) and bid.modifier not in (
        BidModifier.ALMINDELIG,
        BidModifier.GODE,
    ):
        return 2
    return 1


def vip_multiplier(flip_count: int, vip_trump: Suit, ruleset: Ruleset) -> int:
    if flip_count <= 0:
        return 1
    mult = flip_count
    if ruleset.vip_clubs_sans_bonus and vip_trump in _VIP_DOUBLE_SUITS:
        mult *= 2
    return mult


def banket_multiplier(banket: bool, re_banket: bool) -> int:
    if re_banket:
        return 4
    if banket:
        return 2
    return 1


def overtrick_multiplier(relative_score: int) -> int:
    if relative_score >= 0:
        return relative_score + 1
    return relative_score * 2


def score_magnitude(ctx: ScoringContext) -> int:
    base = base_points(ctx.bid, ctx.ruleset)
    base *= modifier_multiplier(ctx.bid)
    if isinstance(ctx.bid, NumberBid) and ctx.bid.modifier == BidModifier.VIP:
        base *= vip_multiplier(ctx.vip_flip_count, ctx.trump, ctx.ruleset)
    base *= banket_multiplier(ctx.banket, ctx.re_banket)
    relative = ctx.tricks_taken_by_declarer_side - ctx.tricks_target
    return base * overtrick_multiplier(relative)


def distribute(
    magnitude: int,
    declarer: Player,
    partner: Player | None,
    all_active: list[Player],
    *,
    selvmakker: bool,
    ruleset: Ruleset,
) -> dict[Player, int]:
    """Zero-sum distribution of a signed magnitude to the 4 seats."""
    deltas: dict[Player, int] = dict.fromkeys(all_active, 0)

    if selvmakker or partner is None:
        declarer_gain = int(magnitude * ruleset.selvmakker_multiplier)
        opponents = [p for p in all_active if p != declarer]
        if not opponents:
            return deltas
        per_opp = declarer_gain // len(opponents)
        deltas[declarer] = per_opp * len(opponents)
        for opp in opponents:
            deltas[opp] = -per_opp
        return deltas

    opponents = [p for p in all_active if p not in (declarer, partner)]
    if not opponents:
        return deltas
    per_opp = (2 * magnitude) // len(opponents)
    total_paid = per_opp * len(opponents)
    deltas[declarer] = total_paid // 2
    deltas[partner] = total_paid - deltas[declarer]
    for opp in opponents:
        deltas[opp] = -per_opp
    return deltas


def is_selvmakker(state_partners: Partners, declarer: Player) -> bool:
    team_id = state_partners.team_id(declarer)
    return state_partners.team_size(team_id) == 1
