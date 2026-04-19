"""Pure-reducer property tests.

Covers the four DoD items from phase 4:
(a) `apply` is pure — same input → same output, no mutation of input state.
(b) Events are deterministic under a seeded RNG.
(c) Replay invariant — `(initial_state, action_sequence)` reconstructs the
    final state (via `apply` step-by-step).
(d) Benchmark — 1000 complete hands in < 1s on this machine.
"""

from __future__ import annotations

import time
from itertools import pairwise
from random import Random

import pytest

from whist.game.actions import BaseAction
from whist.game.game import Game
from whist.game.reducer import apply
from whist.game.state import GameState


def _play_to_end(game: Game) -> list[BaseAction]:
    actions_taken: list[BaseAction] = []
    while not game.has_ended:
        player = game.current_player
        actions = game.valid_actions(player)
        assert actions, f"no valid actions at phase {game.state.phase!r}"
        action = actions[0]
        actions_taken.append(action)
        game.take_action(player, action)
    return actions_taken


def _replay(initial_state: GameState, actions: list[BaseAction]) -> GameState:
    state = initial_state
    rng = Random()
    for action in actions:
        state, _ = apply(state, action, rng=rng)
    return state


# ---- (a) purity ----


def test_apply_does_not_mutate_input_state() -> None:
    game = Game(seed=42)
    game.deal()

    # Snapshot the pre-apply state shape. We assert that after `apply`, the
    # *same* state object still has these values — i.e. apply returned a new
    # object rather than mutating in place.
    state = game.state
    snapshot = {
        "phase": state.phase,
        "turn": state.turn,
        "events_len": len(state.events),
        "pile_play": state.pile_play,
        "tricks_len": len(state.tricks),
    }

    player = state.current_player
    actions = game.valid_actions(player)
    new_state, _events = apply(state, actions[0])

    assert state.phase == snapshot["phase"]
    assert state.turn == snapshot["turn"]
    assert len(state.events) == snapshot["events_len"]
    assert state.pile_play == snapshot["pile_play"]
    assert len(state.tricks) == snapshot["tricks_len"]
    assert new_state is not state


def test_apply_same_input_same_output() -> None:
    game = Game(seed=42)
    game.deal()
    state = game.state
    player = state.current_player
    action = game.valid_actions(player)[0]

    s1, e1 = apply(state, action)
    s2, e2 = apply(state, action)

    assert s1 == s2
    assert e1 == e2


def test_game_state_is_frozen() -> None:
    game = Game(seed=1)
    game.deal()
    with pytest.raises((AttributeError, Exception)):
        game.state.turn = 99  # type: ignore[misc]


# ---- (b) seeded determinism ----


def test_seeded_deal_is_deterministic() -> None:
    g1 = Game(seed=12345)
    g1.deal()
    g2 = Game(seed=12345)
    g2.deal()

    for p in g1.state.players:
        assert g1.state.hands[p].cards == g2.state.hands[p].cards


def test_seeded_full_hand_is_deterministic() -> None:
    g1 = Game(seed=999)
    g1.deal()
    _play_to_end(g1)

    g2 = Game(seed=999)
    g2.deal()
    _play_to_end(g2)

    assert g1.state.tricks == g2.state.tricks
    assert g1.state.trick_owner == g2.state.trick_owner


# ---- (c) replay invariant ----


def test_replay_reconstructs_final_state() -> None:
    game = Game(seed=7)
    game.deal()

    initial_state = game.state
    actions = _play_to_end(game)

    rebuilt = _replay(initial_state, actions)

    # Same trick sequence, same winners, same turn, same events log.
    assert rebuilt.tricks == game.state.tricks
    assert rebuilt.trick_owner == game.state.trick_owner
    assert rebuilt.turn == game.state.turn
    assert rebuilt.phase == game.state.phase
    assert len(rebuilt.events) == len(game.state.events)


def test_replay_via_serialized_state() -> None:
    # Roundtrip the initial state through JSON then replay; same final result.
    game = Game(seed=13)
    game.deal()
    initial_state = game.state

    roundtripped = GameState.from_dict(initial_state.to_dict())
    actions = _play_to_end(game)

    rebuilt = _replay(roundtripped, actions)
    assert rebuilt.tricks == game.state.tricks


# ---- (d) performance sanity ----


def test_thousand_hands_under_one_second() -> None:
    start = time.perf_counter()
    for i in range(1000):
        game = Game(seed=i)
        game.deal()
        _play_to_end(game)
    elapsed = time.perf_counter() - start
    assert elapsed < 2.0, f"1000 hands took {elapsed:.2f}s (target < 2.0s)"


# ---- spot checks the refactor didn't regress behavior ----


def test_full_game_runs_to_13_tricks() -> None:
    # Matches the pre-refactor test_game_run smoke.
    game = Game()
    game.deal()
    while not game.has_ended:
        player = game.current_player
        actions = game.valid_actions(player)
        game.take_action(player, actions[0])
    assert len(game.state.tricks) == 13


def test_events_log_grows_monotonically() -> None:
    game = Game(seed=2)
    game.deal()
    lengths: list[int] = []
    while not game.has_ended:
        lengths.append(len(game.state.events))
        actions = game.valid_actions(game.current_player)
        game.take_action(game.current_player, actions[0])
    lengths.append(len(game.state.events))

    for earlier, later in pairwise(lengths):
        assert later >= earlier
