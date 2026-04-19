"""Phase 10 — Match + scoreboard + session end modes."""

from __future__ import annotations

from whist.game.actions import JernhaandDeclineAction
from whist.game.game import Game
from whist.game.phase import Phase
from whist.game.player import Player
from whist.match.match import Match
from whist.match.scoreboard import Scoreboard
from whist.match.session import SessionConfig


def _play_hand_to_finished(game: Game) -> None:
    """Drive `game` from its current phase to FINISHED via actions[0]."""
    safety = 500
    while game.state.phase != Phase.FINISHED and safety > 0:
        if game.state.phase == Phase.DEALING and not game.state.hands[game.state.players[0]].cards:
            game.deal()
            safety -= 1
            continue
        if game.state.phase == Phase.DEALING and game.state.jernhaand_pending:
            p = next(iter(game.state.jernhaand_pending))
            game.take_action(p, JernhaandDeclineAction(p))
            safety -= 1
            continue
        actions = game.valid_actions(game.current_player)
        if not actions:
            raise RuntimeError(f"stuck at {game.state.phase!r}")
        game.take_action(game.current_player, actions[0])
        safety -= 1


def _players(n: int) -> list[Player]:
    names = ("north", "east", "south", "west", "guest1", "guest2")
    return [Player(i, names[i]) for i in range(n)]


def test_four_player_match_plays_one_hand_and_updates_scoreboard() -> None:
    match = Match(seed=1)
    players = _players(4)
    match.register(players)
    game = match.start_hand()
    _play_hand_to_finished(game)
    match.finish_hand(game)
    assert match.state.hand_count == 1
    # Zero-sum across all players.
    assert sum(match.scoreboard.totals.values()) == 0


def test_five_player_match_sit_out() -> None:
    match = Match(seed=2)
    players = _players(5)
    match.register(players)
    # Pick first 4 as active; player 4 sits out.
    active = players[:4]
    game = match.start_hand(active=active)
    assert players[4] in match.state.next_sitting_out
    _play_hand_to_finished(game)
    match.finish_hand(game)
    # Sitting-out player's score is unchanged.
    assert match.scoreboard.totals[players[4].id] == 0


def test_fixed_hands_end_mode() -> None:
    match = Match(seed=3)
    players = _players(4)
    match.register(
        players, session_config=SessionConfig(end_mode="fixed_hands", fixed_hands_count=2)
    )
    for _ in range(2):
        game = match.start_hand()
        _play_hand_to_finished(game)
        match.finish_hand(game)
    assert match.has_ended


def test_target_points_end_mode() -> None:
    match = Match(seed=4)
    players = _players(4)
    match.register(players, session_config=SessionConfig(end_mode="target_points", target_points=1))
    # Artificially spike one player's score.
    match.state.scoreboard.apply_deltas({players[0].id: 10})
    assert match.has_ended


def test_scoreboard_roundtrip() -> None:
    sb = Scoreboard()
    sb.apply_deltas({0: 100, 1: -50, 2: 25, 3: -75})
    assert Scoreboard.from_dict(sb.to_dict()).totals == sb.totals
