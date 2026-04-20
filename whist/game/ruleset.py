"""Configurable rule flags.

A `Ruleset` instance is attached to the session envelope (`Match`) and consulted
by the reducer for every rule-branching decision — no magic numbers in the
reducer. `Ruleset` itself is immutable; variants don't change mid-session.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Literal


class BidModifier(StrEnum):
    ALMINDELIG = "almindelig"
    GODE = "gode"
    HALVE = "halve"
    VIP = "vip"
    SANS = "sans"


class NoloContract(StrEnum):
    SOL = "sol"
    REN_SOL = "ren_sol"
    BORDLAEGGER = "bordlaegger"
    REN_BORDLAEGGER = "ren_bordlaegger"


KattenExchangeMode = Literal["all_or_nothing", "freeform_0_to_3"]
HalveExchanger = Literal["declarer", "partner"]
FirstLead = Literal["forhand", "declarer"]
NoloSettlement = Literal["solo_each", "vs_nonparticipating", "partners"]
Variant = Literal["esmakker", "classic", "bid_whist"]
ClassicTrumpSource = Literal["last_card", "fixed", "none"]


DEFAULT_BID_MODIFIERS: frozenset[BidModifier] = frozenset(
    {
        BidModifier.GODE,
        BidModifier.HALVE,
        BidModifier.VIP,
        BidModifier.SANS,
    }
)

DEFAULT_MODIFIER_ORDER: tuple[BidModifier, ...] = (
    BidModifier.GODE,
    BidModifier.HALVE,
    BidModifier.VIP,
    BidModifier.SANS,
)

DEFAULT_NOLO_LADDER: tuple[NoloContract, ...] = (
    NoloContract.SOL,
    NoloContract.REN_SOL,
    NoloContract.BORDLAEGGER,
    NoloContract.REN_BORDLAEGGER,
)


@dataclass(frozen=True)
class Ruleset:
    """Rule-of-play flags. One instance per `Match`.

    Defaults cover the canonical call-ace variant. Use `Ruleset.default()` for
    the human preset, `Ruleset.classic()` for plain partnership whist, and
    `Ruleset.bid_whist()` for American bid whist.
    """

    # --- variant selection ---
    variant: Variant = "esmakker"

    # --- bidding (esmakker) ---
    minimum_bid: int = 7
    bid_modifiers: frozenset[BidModifier] = field(default_factory=lambda: DEFAULT_BID_MODIFIERS)
    modifier_order: tuple[BidModifier, ...] = DEFAULT_MODIFIER_ORDER
    nolo_ladder: tuple[NoloContract, ...] = DEFAULT_NOLO_LADDER
    klor_legal_in_almindelig: bool = False

    # --- exchange (katten / halve / vip) ---
    katten_exchange_mode: KattenExchangeMode = "all_or_nothing"
    vip_exchange_mandatory: bool = True
    halve_exchanger: HalveExchanger = "partner"

    # --- play ---
    first_lead: FirstLead = "forhand"
    partner_ace_same_suit_as_trump: bool = False
    marker_card_threshold: int = 1
    marker_card_can_trump: bool = False

    # --- scoring ---
    selvmakker_multiplier: float = 3.0
    banket_enabled: bool = True
    banket_window_tricks: int | None = 3
    nolo_gaa_med_settlement: NoloSettlement = "solo_each"
    vip_clubs_sans_bonus: bool = True
    bordlaegger_base_points: int = 200
    ren_bordlaegger_base_points: int = 400

    # --- classic whist ---
    classic_trump_source: ClassicTrumpSource = "last_card"
    classic_fixed_trump: str | None = None

    # --- bid whist ---
    bid_whist_kitty_size: int = 6
    bid_whist_allow_no_trump: bool = True
    bid_whist_min_bid: int = 4

    @classmethod
    def default(cls) -> Ruleset:
        """Canonical call-ace preset."""
        return cls()

    @classmethod
    def ai_training(cls) -> Ruleset:
        """Preset used by `WhistEnv` for RL training.

        Currently identical to `default()` — kept as a distinct preset so
        RL-specific simplifications (e.g. disabling banket to shrink the
        action space) can land here without touching the human game.
        """
        return cls()

    @classmethod
    def classic(cls) -> Ruleset:
        """Classic partnership whist — no bidding, fixed partners, last-card trump."""
        return cls(variant="classic")

    @classmethod
    def bid_whist(cls) -> Ruleset:
        """American bid whist — bidding for books, kitty exchange, fixed partnerships."""
        return cls(variant="bid_whist")

    def to_dict(self) -> dict[str, Any]:
        return {
            "variant": self.variant,
            "minimum_bid": self.minimum_bid,
            "bid_modifiers": sorted(m.value for m in self.bid_modifiers),
            "modifier_order": [m.value for m in self.modifier_order],
            "nolo_ladder": [n.value for n in self.nolo_ladder],
            "klor_legal_in_almindelig": self.klor_legal_in_almindelig,
            "katten_exchange_mode": self.katten_exchange_mode,
            "vip_exchange_mandatory": self.vip_exchange_mandatory,
            "halve_exchanger": self.halve_exchanger,
            "first_lead": self.first_lead,
            "partner_ace_same_suit_as_trump": self.partner_ace_same_suit_as_trump,
            "marker_card_threshold": self.marker_card_threshold,
            "marker_card_can_trump": self.marker_card_can_trump,
            "selvmakker_multiplier": self.selvmakker_multiplier,
            "banket_enabled": self.banket_enabled,
            "banket_window_tricks": self.banket_window_tricks,
            "nolo_gaa_med_settlement": self.nolo_gaa_med_settlement,
            "vip_clubs_sans_bonus": self.vip_clubs_sans_bonus,
            "bordlaegger_base_points": self.bordlaegger_base_points,
            "ren_bordlaegger_base_points": self.ren_bordlaegger_base_points,
            "classic_trump_source": self.classic_trump_source,
            "classic_fixed_trump": self.classic_fixed_trump,
            "bid_whist_kitty_size": self.bid_whist_kitty_size,
            "bid_whist_allow_no_trump": self.bid_whist_allow_no_trump,
            "bid_whist_min_bid": self.bid_whist_min_bid,
        }

    @classmethod
    def from_dict(cls, d: Mapping[str, Any]) -> Ruleset:
        return cls(
            variant=d.get("variant", "esmakker"),
            minimum_bid=int(d["minimum_bid"]),
            bid_modifiers=frozenset(BidModifier(v) for v in d["bid_modifiers"]),
            modifier_order=tuple(BidModifier(v) for v in d["modifier_order"]),
            nolo_ladder=tuple(NoloContract(v) for v in d["nolo_ladder"]),
            klor_legal_in_almindelig=bool(d["klor_legal_in_almindelig"]),
            katten_exchange_mode=d["katten_exchange_mode"],
            vip_exchange_mandatory=bool(d["vip_exchange_mandatory"]),
            halve_exchanger=d["halve_exchanger"],
            first_lead=d["first_lead"],
            partner_ace_same_suit_as_trump=bool(d["partner_ace_same_suit_as_trump"]),
            marker_card_threshold=int(d["marker_card_threshold"]),
            marker_card_can_trump=bool(d["marker_card_can_trump"]),
            selvmakker_multiplier=float(d["selvmakker_multiplier"]),
            banket_enabled=bool(d["banket_enabled"]),
            banket_window_tricks=(
                None if d["banket_window_tricks"] is None else int(d["banket_window_tricks"])
            ),
            nolo_gaa_med_settlement=d["nolo_gaa_med_settlement"],
            vip_clubs_sans_bonus=bool(d["vip_clubs_sans_bonus"]),
            bordlaegger_base_points=int(d["bordlaegger_base_points"]),
            ren_bordlaegger_base_points=int(d["ren_bordlaegger_base_points"]),
            classic_trump_source=d.get("classic_trump_source", "last_card"),
            classic_fixed_trump=d.get("classic_fixed_trump"),
            bid_whist_kitty_size=int(d.get("bid_whist_kitty_size", 6)),
            bid_whist_allow_no_trump=bool(d.get("bid_whist_allow_no_trump", True)),
            bid_whist_min_bid=int(d.get("bid_whist_min_bid", 4)),
        )


__all__ = [
    "DEFAULT_BID_MODIFIERS",
    "DEFAULT_MODIFIER_ORDER",
    "DEFAULT_NOLO_LADDER",
    "BidModifier",
    "ClassicTrumpSource",
    "FirstLead",
    "HalveExchanger",
    "KattenExchangeMode",
    "NoloContract",
    "NoloSettlement",
    "Ruleset",
    "Variant",
]
