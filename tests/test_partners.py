import pytest

from whist.game.player import Player
from whist.game.partners import Partners


@pytest.fixture
def players():
    player_names = ("north", "east", "south", "west")
    return [
        Player(id, name)
        for id, name
        in enumerate(player_names)
    ]


@pytest.fixture
def partners(players):
    return Partners(players)


def test_init(partners):
    assert partners.num_teams == len(partners.players)


def test_join_pair(partners):

    p0 = partners.players[0]
    p1 = partners.players[1]

    partners.join(p0, p1)

    assert partners.num_teams == len(partners.players)-1

    assert partners.team_id(p0) == partners.team_id(p1)

    team_id = partners.team_id(p0)
    assert partners.team_size(team_id) == 2


def test_isolate(partners):

    p0 = partners.players[0]
    p1 = partners.players[1]

    partners.isolate(p0)

    assert partners.num_teams == 2

    assert partners.team_id(p0) != partners.team_id(p1)

    team_id = partners.team_id(p0)
    assert partners.team_size(team_id) == 1

    team_id = partners.team_id(p1)
    assert partners.team_size(team_id) == len(partners.players)-1


def test_bisect(partners):

    p0 = partners.players[0]
    p1 = partners.players[1]

    partners.bisect(p0, p1)

    assert partners.num_teams == 2

    assert partners.team_id(p0) == partners.team_id(p1)

