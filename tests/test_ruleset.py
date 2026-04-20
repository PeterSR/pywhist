"""Pin the default Ruleset preset values.

If a default drifts, this test fails and forces someone to either (a) update
the pinned values, or (b) revert the drift. Without this, a reducer branch
could silently flip a default and nobody would notice until a hand scored
wrong.
"""

from __future__ import annotations

import pytest

from whist.game.game import Game
from whist.game.ruleset import (
    DEFAULT_BID_MODIFIERS,
    DEFAULT_MODIFIER_ORDER,
    DEFAULT_NOLO_LADDER,
    BidModifier,
    NoloContract,
    Ruleset,
)
from whist.match.session import SessionConfig
from whist.match.state import MatchState

# ---- default preset pinned ----


def test_default_preset_pinned_values() -> None:
    r = Ruleset.default()

    # Bidding
    assert r.minimum_bid == 7
    assert r.bid_modifiers == frozenset(
        {BidModifier.GODE, BidModifier.HALVE, BidModifier.VIP, BidModifier.SANS}
    )
    assert r.modifier_order == (
        BidModifier.GODE,
        BidModifier.HALVE,
        BidModifier.VIP,
        BidModifier.SANS,
    )
    assert r.nolo_ladder == (
        NoloContract.SOL,
        NoloContract.REN_SOL,
        NoloContract.BORDLAEGGER,
        NoloContract.REN_BORDLAEGGER,
    )
    assert r.klor_legal_in_almindelig is False

    # Exchange
    assert r.katten_exchange_mode == "all_or_nothing"
    assert r.vip_exchange_mandatory is True
    assert r.halve_exchanger == "partner"

    # Play
    assert r.first_lead == "forhand"
    assert r.partner_ace_same_suit_as_trump is False
    assert r.marker_card_threshold == 1
    assert r.marker_card_can_trump is False

    # Scoring
    assert r.selvmakker_multiplier == 3.0
    assert r.banket_enabled is True
    assert r.banket_window_tricks == 3
    assert r.nolo_gaa_med_settlement == "solo_each"
    assert r.vip_clubs_sans_bonus is True
    assert r.bordlaegger_base_points == 200
    assert r.ren_bordlaegger_base_points == 400


def test_ai_training_currently_matches_default() -> None:
    # ai_training() is a distinct preset so we can drift it without touching
    # the human default. For now the two are equal by construction.
    assert Ruleset.ai_training() == Ruleset.default()


def test_ruleset_is_hashable() -> None:
    # Frozen + immutable fields (tuples, frozensets) → hashable. Worth pinning
    # because Match wants to key caches or records off a ruleset identity.
    hash(Ruleset.default())


def test_ruleset_is_frozen() -> None:
    r = Ruleset.default()
    with pytest.raises((AttributeError, Exception)):
        r.minimum_bid = 8  # type: ignore[misc]


def test_defaults_consistent_with_module_level_constants() -> None:
    r = Ruleset.default()
    assert r.bid_modifiers == DEFAULT_BID_MODIFIERS
    assert r.modifier_order == DEFAULT_MODIFIER_ORDER
    assert r.nolo_ladder == DEFAULT_NOLO_LADDER


# ---- serialize roundtrip ----


def test_ruleset_roundtrip() -> None:
    r = Ruleset.default()
    assert Ruleset.from_dict(r.to_dict()) == r


def test_ruleset_roundtrip_non_default() -> None:
    r = Ruleset(
        minimum_bid=8,
        banket_enabled=False,
        banket_window_tricks=None,
        marker_card_threshold=0,
        klor_legal_in_almindelig=True,
    )
    assert Ruleset.from_dict(r.to_dict()) == r


# ---- SessionConfig ----


def test_session_config_default() -> None:
    sc = SessionConfig()
    assert sc.end_mode == "open"
    assert sc.fixed_hands_count is None
    assert sc.target_points is None
    assert sc.time_limit_seconds is None
    assert sc.sit_out_rotation == "manual"


def test_session_config_ai_default_spec() -> None:
    sc = SessionConfig.ai_default()
    assert sc.end_mode == "fixed_hands"
    assert sc.fixed_hands_count == 100


def test_session_config_roundtrip() -> None:
    sc = SessionConfig.ai_default()
    assert SessionConfig.from_dict(sc.to_dict()) == sc


def test_session_config_is_frozen() -> None:
    sc = SessionConfig()
    with pytest.raises((AttributeError, Exception)):
        sc.end_mode = "time"  # type: ignore[misc]


# ---- plumbing: Game accepts a ruleset, MatchState exposes both ----


def test_game_has_default_ruleset() -> None:
    g = Game()
    assert g.ruleset == Ruleset.default()


def test_game_accepts_custom_ruleset() -> None:
    custom = Ruleset(minimum_bid=8)
    g = Game(ruleset=custom)
    assert g.ruleset is custom


def test_match_state_exposes_ruleset_and_session() -> None:
    ms = MatchState()
    assert ms.ruleset == Ruleset.default()
    assert ms.session_config == SessionConfig()
