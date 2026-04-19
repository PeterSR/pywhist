import pytest

from whist.game import Game
from whist.game.actions import JernhaandDeclineAction
from whist.game.phase import Phase


@pytest.fixture
def game():
    return Game(seed=42)


def test_game_run(game):
    game.deal()

    safety = 500
    while not game.has_ended and safety > 0:
        state = game.state
        if state.phase == Phase.DEALING and state.jernhaand_pending:
            p = next(iter(state.jernhaand_pending))
            game.take_action(p, JernhaandDeclineAction(p))
            safety -= 1
            continue

        player = game.current_player
        actions = game.valid_actions(player)
        if not actions:
            raise RuntimeError(f"no actions at phase {state.phase!r}")
        game.take_action(player, actions[0])
        safety -= 1

    assert len(game.state.tricks) == 13
