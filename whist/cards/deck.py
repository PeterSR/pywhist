from __future__ import annotations

import random

from dataclasses import dataclass
from typing import List

from .suits import Suit, suits
from .ranks import ranks
from .cards import Card
from .trick import Trick


@dataclass
class Deck:
    cards: List[Card]
    allow_reorder: bool = True

    @staticmethod
    def empty() -> Deck:
        return Deck([])

    @staticmethod
    def empty_pile() -> Deck:
        deck = Deck.empty()
        deck.allow_reorder = False
        return deck

    @staticmethod
    def from_deck(other: Deck):
        return Deck(other.cards.copy())

    @staticmethod
    def full_deck(num_jokers=3):
        deck = Deck.empty()

        for suit in suits:
            for rank in ranks:
                deck.cards.append(Card(suit, rank))

        for _ in range(num_jokers):
            deck.cards.append(Card.joker)

        return deck

    def sort(self, trump=Suit.Unknown):
        if self.allow_reorder:
            self.cards.sort()

    def shuffle(self):
        if self.allow_reorder:
            random.shuffle(self.cards)

    def take(self, card: Card):
        return self.cards.remove(card)

    def give(self, card: Card, sort=True):
        self.cards.append(card)
        if sort:
            self.sort()

    def to_trick(self) -> Trick:
        if len(self) != 4:
            raise ValueError("to_trick only support tricks of size 4")

        return tuple(self.cards)

    def __len__(self):
        return len(self.cards)

    def __iter__(self):
        return iter(self.cards)

    def __str__(self):
        return " ".join(c.symbol for c in self.cards)