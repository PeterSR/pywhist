"""Phase-machine tests.

The reducer dispatches by `Phase`. Each phase has a handler; phases without
real logic yet raise `NotImplementedError("phase X pending")`. These tests
pin the dispatch surface so adding a new phase without wiring it breaks CI.
"""

from __future__ import annotations

import pytest

from whist.cards import Suit
from whist.errors import IllegalAction, IllegalPhase
from whist.game.actions import CallAction, JernhaandDeclineAction, PassAction, PlayAction
from whist.game.bids import Call
from whist.game.events import PhaseTransitionEvent
from whist.game.game import Game
from whist.game.phase import Phase
from whist.game.reducer import _PHASE_HANDLERS, apply

# phases that still have no real logic — `apply` should raise NotImplementedError
STUB_PHASES: tuple[Phase, ...] = (
    Phase.SCORING,
    Phase.FINISHED,
)


def test_every_phase_has_a_handler() -> None:
    # Regression guard: if `Phase` grows, `_PHASE_HANDLERS` must grow with it.
    missing = set(Phase) - set(_PHASE_HANDLERS)
    assert missing == set(), f"Phase(s) missing a reducer handler: {missing}"


def test_every_phase_has_a_valid_actions_dispatch() -> None:
    missing = set(Phase) - set(Game._VALID_ACTIONS_DISPATCH)
    assert missing == set(), f"Phase(s) missing valid_actions dispatch: {missing}"


@pytest.mark.parametrize("phase", STUB_PHASES)
def test_stub_phases_raise_not_implemented(phase: Phase) -> None:
    game = Game(seed=0)
    game.deal()
    state = game.state.replace(phase=phase)
    with pytest.raises(NotImplementedError, match=phase.value):
        apply(state, PassAction())


def _drive_to_phase(game: Game, target: Phase, safety: int = 200) -> None:
    """Take actions[0] until the state reaches `target` or we run out of moves."""
    while game.state.phase != target and safety > 0:
        state = game.state
        if state.phase == Phase.DEALING and state.jernhaand_pending:
            p = next(iter(state.jernhaand_pending))
            game.take_action(p, JernhaandDeclineAction(p))
            safety -= 1
            continue
        actions = game.valid_actions(game.current_player)
        if not actions:
            raise RuntimeError(f"stuck at phase {state.phase!r}")
        game.take_action(game.current_player, actions[0])
        safety -= 1


def test_bidding_to_calling_transition() -> None:
    game = Game(seed=1)
    game.deal()
    assert game.state.phase == Phase.BIDDING
    _drive_to_phase(game, Phase.CALLING)
    assert game.state.phase == Phase.CALLING


def test_calling_transition_to_banket() -> None:
    game = Game(seed=2)
    game.deal()
    _drive_to_phase(game, Phase.CALLING)

    player = game.current_player
    actions = game.valid_actions(player)
    # Use the first CallAction emitted.
    call_action = next(a for a in actions if isinstance(a, CallAction))
    _state_before_phase = game.state.phase
    _, events = apply(game.state, call_action)
    assert any(
        isinstance(e, PhaseTransitionEvent)
        and e.from_phase == Phase.CALLING
        and e.to_phase == Phase.BANKET
        for e in events
    )


def test_playing_does_not_re_emit_transition() -> None:
    game = Game(seed=3)
    game.deal()
    _drive_to_phase(game, Phase.PLAYING)

    player = game.current_player
    action = game.valid_actions(player)[0]
    assert isinstance(action, PlayAction)
    _, events = apply(game.state, action)

    assert all(not isinstance(e, PhaseTransitionEvent) for e in events)


def test_calling_rejects_non_call_action() -> None:
    game = Game(seed=4)
    game.deal()
    _drive_to_phase(game, Phase.CALLING)
    with pytest.raises(IllegalAction):
        apply(game.state, PassAction())


def test_playing_rejects_non_play_action() -> None:
    game = Game(seed=5)
    game.deal()
    _drive_to_phase(game, Phase.PLAYING)
    with pytest.raises(IllegalAction):
        apply(game.state, CallAction(Call(Suit.Club, Suit.Heart)))


def test_phase_transition_event_roundtrips() -> None:
    event = PhaseTransitionEvent(from_phase=Phase.CALLING, to_phase=Phase.BANKET)
    assert PhaseTransitionEvent.from_dict(event.to_dict()) == event


def test_unknown_phase_raises_illegal_phase() -> None:
    game = Game(seed=6)
    game.deal()
    _drive_to_phase(game, Phase.CALLING)
    # Remove the CALLING handler and assert apply raises IllegalPhase.
    handler = _PHASE_HANDLERS.pop(Phase.CALLING)
    try:
        with pytest.raises(IllegalPhase):
            apply(game.state, CallAction(Call(Suit.Heart, Suit.Spade)))
    finally:
        _PHASE_HANDLERS[Phase.CALLING] = handler
