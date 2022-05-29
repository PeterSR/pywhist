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
        return MatchState(
            game_count=0,
        )

    def new_game(self, **state_settings):
        self.current_game = Game()
        self.current_game.state = self.current_game.initial_state(**state_settings)
        self.state.game_state = self.current_game.state

    @property
    def has_ended(self):
        if self.state.max_game_count == -1:
            return False
        return self.state.game_count > self.state.max_game_count