"""Phase-machine tests.

The reducer dispatches by `Phase`. Each phase has a handler; phases without
real logic yet raise `NotImplementedError("phase X pending")`. These tests
pin the dispatch surface so adding a new phase without wiring it breaks CI.
"""

from __future__ import annotations

import pytest

from whist.cards import Rank, Suit
from whist.errors import IllegalAction, IllegalPhase
from whist.game.actions import CallAction, PlayAction
from whist.game.bids import Call
from whist.game.events import PhaseTransitionEvent
from whist.game.game import Game
from whist.game.phase import Phase
from whist.game.reducer import _PHASE_HANDLERS, apply


def test_every_phase_has_a_handler() -> None:
    # Regression guard: if `Phase` grows, `_PHASE_HANDLERS` must grow with it.
    missing = set(Phase) - set(_PHASE_HANDLERS)
    assert missing == set(), f"Phase(s) missing a reducer handler: {missing}"


def test_every_phase_has_a_valid_actions_dispatch() -> None:
    missing = set(Phase) - set(Game._VALID_ACTIONS_DISPATCH)
    assert missing == set(), f"Phase(s) missing valid_actions dispatch: {missing}"


def test_stub_phases_raise_not_implemented() -> None:
    # Phase 5 stubs should raise NotImplementedError with a "phase X pending"
    # message so someone tripping one gets pointed at the landing phase.
    game = Game(seed=0)
    game.deal()
    # Hand-make a fake state pinned to BIDDING and call apply on it.
    state_in_bidding = game.state.replace(phase=Phase.BIDDING)
    with pytest.raises(NotImplementedError, match="bidding"):
        apply(state_in_bidding, CallAction(Call(Suit.Club, Suit.Heart)))


@pytest.mark.parametrize(
    ("phase", "fragment"),
    [
        (Phase.DEALING, "dealing"),
        (Phase.BIDDING, "bidding"),
        (Phase.BANKET, "banket"),
        (Phase.KATTEN_EXCHANGE, "katten_exchange"),
        (Phase.VIP_FLIP, "vip_flip"),
        (Phase.HALVE_TRUMP, "halve_trump"),
        (Phase.MARKER_PLACEMENT, "marker_placement"),
        (Phase.SCORING, "scoring"),
        (Phase.FINISHED, "finished"),
    ],
)
def test_stub_phases_message(phase: Phase, fragment: str) -> None:
    game = Game(seed=0)
    game.deal()
    state = game.state.replace(phase=phase)
    with pytest.raises(NotImplementedError, match=fragment):
        apply(state, CallAction(Call(Suit.Club, Suit.Heart)))


def test_calling_transition_emits_phase_event() -> None:
    game = Game(seed=1)
    game.deal()
    assert game.state.phase == Phase.CALLING

    action = CallAction(Call(Suit.Heart, Suit.Spade))
    new_state, events = apply(game.state, action)

    assert new_state.phase == Phase.PLAYING
    transitions = [e for e in events if isinstance(e, PhaseTransitionEvent)]
    assert len(transitions) == 1
    assert transitions[0].from_phase == Phase.CALLING
    assert transitions[0].to_phase == Phase.PLAYING


def test_playing_does_not_re_emit_transition() -> None:
    game = Game(seed=2)
    game.deal()
    game.take_action(game.current_player, CallAction(Call(Suit.Heart, Suit.Spade)))

    # Now in PLAYING; a PlayAction stays within PLAYING and should NOT emit a
    # PhaseTransitionEvent.
    player = game.current_player
    action = game.valid_actions(player)[0]
    assert isinstance(action, PlayAction)
    _, events = apply(game.state, action)

    assert all(not isinstance(e, PhaseTransitionEvent) for e in events)


def test_calling_rejects_non_call_action() -> None:
    game = Game(seed=3)
    game.deal()
    with pytest.raises(IllegalAction):
        apply(
            game.state,
            PlayAction(__import__("whist").cards.Card(Suit.Club, Rank.Two)),
        )


def test_playing_rejects_non_play_action() -> None:
    game = Game(seed=4)
    game.deal()
    game.take_action(game.current_player, CallAction(Call(Suit.Heart, Suit.Spade)))
    with pytest.raises(IllegalAction):
        apply(game.state, CallAction(Call(Suit.Club, Suit.Heart)))


def test_phase_transition_event_roundtrips() -> None:
    event = PhaseTransitionEvent(from_phase=Phase.CALLING, to_phase=Phase.PLAYING)
    assert PhaseTransitionEvent.from_dict(event.to_dict()) == event


def test_unknown_phase_raises_illegal_phase() -> None:
    # Only real `Phase` values survive the dispatch; a future phase added to
    # `Phase` without adding a handler would fail `test_every_phase_has_a_handler`
    # first, but we also guard at the dispatch site itself.
    game = Game(seed=5)
    game.deal()
    # Fake an unregistered phase by deleting one from the dispatch temporarily.
    handler = _PHASE_HANDLERS.pop(Phase.CALLING)
    try:
        with pytest.raises(IllegalPhase):
            apply(game.state, CallAction(Call(Suit.Heart, Suit.Spade)))
    finally:
        _PHASE_HANDLERS[Phase.CALLING] = handler
