"""Smoke tests for the error hierarchy and Phase enum.

The rest of the error-raising sites arrive with later phases; this test just
asserts the shape and that `game.Game` raises the right types at boundaries
that exist today.
"""

import pytest

from whist.errors import (
    IllegalAction,
    IllegalPhase,
    RulesViolation,
    VariantMismatch,
    WhistError,
)
from whist.game import Game
from whist.game.phase import Phase


def test_hierarchy():
    for cls in (IllegalAction, IllegalPhase, RulesViolation, VariantMismatch):
        assert issubclass(cls, WhistError)


def test_take_action_rejects_non_action():
    game = Game()
    game.deal()
    with pytest.raises(TypeError, match="Not an action"):
        game.take_action(game.current_player, "not an action")


def test_valid_actions_returns_empty_during_dealing():
    # Phase 5 turned the phase machine into a dispatch table: phases with no
    # player-facing actions return `[]` rather than raising. DEALING is one of
    # those (no one acts during the deal).
    game = Game()
    assert game.state.phase == Phase.DEALING
    assert game.valid_actions(game.current_player) == []


def test_phase_strenum_roundtrips_as_string():
    # JSON roundtrip relies on the StrEnum behavior.
    assert str(Phase.BIDDING) == "bidding"
    assert Phase("bidding") is Phase.BIDDING
