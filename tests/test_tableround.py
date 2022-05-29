import pytest

from whist.game.player import Player
from whist.game.tableround import TableRound


@pytest.fixture
def players():
    player_names = ("north", "east", "south", "west")
    return [
        Player(id, name)
        for id, name
        in enumerate(player_names)
    ]


def test_tableround(players):

    dealer = players[2]
    tableround = TableRound(dealer, players)

    iter_players = [p for p in tableround]

    p = players
    assert iter_players == [p[3], p[0], p[1], p[2]]


def test_tableround_2_rounds(players):
    dealer = players[2]
    tableround = TableRound(dealer, players, 2)

    iter_players = [p for p in tableround]

    p = players
    assert iter_players == [p[3], p[0], p[1], p[2]] * 2
