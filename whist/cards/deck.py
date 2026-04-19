from __future__ import annotations

import random
from collections.abc import Iterable, Iterator, Mapping
from dataclasses import dataclass

from .cards import Card
from .ranks import ranks
from .suits import suits
from .trick import Trick


@dataclass
class Deck:
    cards: list[Card]
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
    def from_deck(other: Deck) -> Deck:
        return Deck(other.cards.copy())

    @staticmethod
    def full_deck(num_jokers: int = 3) -> Deck:
        deck = Deck.empty()

        for suit in suits:
            for rank in ranks:
                deck.cards.append(Card(suit, rank))

        for _ in range(num_jokers):
            deck.cards.append(Card.joker)

        return deck

    def sort(self) -> None:
        if self.allow_reorder:
            self.cards.sort()

    def shuffle(self, rng: random.Random | None = None) -> None:
        if not self.allow_reorder:
            return
        if rng is None:
            random.shuffle(self.cards)
        else:
            rng.shuffle(self.cards)

    def take(self, card: Card) -> None:
        self.cards.remove(card)

    def give(self, card: Card, sort: bool = True) -> None:
        self.cards.append(card)
        if sort:
            self.sort()

    def to_trick(self) -> Trick:
        if len(self) != 4:
            raise ValueError("to_trick only support tricks of size 4")

        return tuple(self.cards)  # type: ignore[return-value]

    def to_list(self) -> list[dict[str, str]]:
        return [c.to_dict() for c in self.cards]

    @classmethod
    def from_list(
        cls,
        lst: Iterable[Mapping[str, str]],
        *,
        allow_reorder: bool = True,
    ) -> Deck:
        deck = cls([Card.from_dict(d) for d in lst])
        deck.allow_reorder = allow_reorder
        return deck

    def __len__(self) -> int:
        return len(self.cards)

    def __iter__(self) -> Iterator[Card]:
        return iter(self.cards)

    def __str__(self) -> str:
        return " ".join(c.symbol for c in self.cards)
