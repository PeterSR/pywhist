"""Clockwise iterator over players starting from the dealer + 1.

The pre-revamp version mutated `self` inside `__iter__`, which broke nested
iteration. This version yields a fresh generator each call.
"""

from collections.abc import Iterator
from dataclasses import dataclass

from .player import Player


@dataclass
class TableRound:
    dealer: Player
    players: list[Player]
    max_rounds: int = 1

    def __iter__(self) -> Iterator[Player]:
        n = len(self.players)
        start = (self.players.index(self.dealer) + 1) % n
        for _ in range(self.max_rounds):
            for offset in range(n):
                yield self.players[(start + offset) % n]
