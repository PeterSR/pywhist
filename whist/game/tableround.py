from dataclasses import dataclass
from typing import List

from .player import Player


@dataclass
class TableRound:
    dealer: Player
    players: List[Player]
    max_rounds: int = 1

    def __iter__(self):
        # Start dealing to the next player after the dealer.
        self.index = self.next_index(self.players.index(self.dealer))
        self.start_index = self.index
        self.count = 0
        self.round_count = 0
        return self

    def __next__(self):
        if self.count > 0 and self.index == self.start_index:
            self.round_count += 1

            if self.round_count >= self.max_rounds:
                raise StopIteration

        p = self.players[self.index]
        self.count += 1
        self.index = self.next_index(self.index)
        return p

    def next_index(self, index):
        return (index + 1) % len(self.players)
