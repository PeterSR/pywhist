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

    def __str__(self):
        return f"Played {self.card.symbol}"
