from dataclasses import dataclass

from ..cards import Trick
from .actions import BaseAction
from .partners import TeamID
from .player import Player


class BaseEvent:
    pass


@dataclass(frozen=True)
class ActionTakenEvent(BaseEvent):
    player: Player
    action: BaseAction

    def __str__(self) -> str:
        return f"Player {self.player.name}: {self.action}"


@dataclass(frozen=True)
class TrickTakenEvent(BaseEvent):
    player: Player
    team_id: TeamID
    trick: Trick

    def __str__(self) -> str:
        trick_symbols = tuple(card.symbol for card in self.trick)
        return f"Player {self.player.name} took {trick_symbols}"
