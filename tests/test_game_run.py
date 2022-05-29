import pytest

from whist.game import Game


@pytest.fixture
def game():
    return Game()


def test_game_run(game):
    game.deal()

    while not game.has_ended:
        player = game.current_player
        actions = game.valid_actions(player)
        action = actions[0]
        game.take_action(player, action)

    assert len(game.state.tricks) == 13