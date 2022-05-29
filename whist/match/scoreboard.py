from typing import Dict

from ..game.player import PlayerID
from ..game.scoring import Score

# Only a type for now
Scoreboard = Dict[PlayerID, Score]
