from dataclasses import dataclass

from ..game import Game
from .state import MatchState


@dataclass
class Match:
    """
    Represents the game logic for a match of n games
    """

    current_game: Game = None
    state: MatchState = None

    def __post_init__(self):
        if self.state is None:
            self.state = self.initial_state()

    def initial_state(self, **settings):
        pass