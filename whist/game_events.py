from dataclasses import dataclass

from .cards import Trick
from .player import Player
from .game_actions import BaseAction


class BaseEvent:
    pass


@dataclass(frozen=True)
class ActionTakenEvent(BaseEvent):
    player: Player
    action: BaseAction

@dataclass(frozen=True)
class TrickTakenEvent(BaseEvent):
    player: Player
    trick: Trick


