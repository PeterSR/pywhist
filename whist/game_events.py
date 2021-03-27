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

    def __str__(self):
        return f"Player {self.player.name}: {self.action}"


@dataclass(frozen=True)
class TrickTakenEvent(BaseEvent):
    player: Player
    trick: Trick

    def __str__(self):
        trick_symbols = tuple(card.symbol for card in self.trick)
        return f"Player {self.player.name} took {trick_symbols}"
