from dataclasses import dataclass

from .player import Player
from .cards import Card


class BaseAction:
    """
    Base class for game actions
    """


@dataclass(frozen=True)
class PlayAction(BaseAction):
    card: Card
