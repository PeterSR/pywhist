from dataclasses import dataclass

from ..game import Game
from .state import MatchState


@dataclass
class Match:
    """
    Represents the game logic for a match of n games
    """

    _current_game: Game = None
    state: MatchState = None

    def __post_init__(self):
        if self.state is None:
            self.state = self.initial_state()

    def initial_state(self, **settings):
        return MatchState(
            game_count=0,
        )

    @property
    def current_game(self) -> Game:
        return self._current_game

    @current_game.setter
    def current_game(self, g: Game):
        self._current_game = g
        self.state.game_state = self._current_game.state

    def new_game(self):
        self.current_game = Game()

    @property
    def has_ended(self):
        if self.state.max_game_count == -1:
            return False
        return self.state.game_count > self.state.max_game_count