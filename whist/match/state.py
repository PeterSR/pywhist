from dataclasses import dataclass

from ..game.player import PlayerID
from ..game.ruleset import Ruleset
from ..game.state import GameState
from .scoreboard import Scoreboard
from .session import SessionConfig


@dataclass
class MatchState:
    """
    Represents the state for a match of n games
    """

    game_state: GameState = None
    game_count: int = 0
    max_game_count: int = -1  # -1 for infinite
    scoreboard: Scoreboard = None
    ruleset: Ruleset = None
    session_config: SessionConfig = None

    def __post_init__(self):
        if self.scoreboard is None:
            self.scoreboard = dict()
        if self.ruleset is None:
            self.ruleset = Ruleset.petersmakker()
        if self.session_config is None:
            self.session_config = SessionConfig()

    @property
    def players(self) -> list[PlayerID]:
        return list(self.scoreboard.keys())
