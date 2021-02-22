from dataclasses import dataclass
from enum import Enum, auto


class Suit(Enum):
    Club = auto()
    Diamond = auto()
    Heart = auto()
    Spade = auto()

    @property
    def symbol(self):
        return suit_symbol[self]


suit_symbol = {
    Suit.Club: "♣",
    Suit.Diamond: "♦",
    Suit.Heart: "♥",
    Suit.Spade: "♠",
}


class Rank(Enum):
    Ace = auto()
    Two = auto()
    Three = auto()
    Four = auto()
    Five = auto()
    Six = auto()
    Seven = auto()
    Eight = auto()
    Nine = auto()
    Ten = auto()
    Jack = auto()
    Queen = auto()
    King = auto()
    Joker = auto()

    @property
    def symbol(self):
        return rank_symbol[self]


rank_symbol = {
    Rank.Ace: "A",
    Rank.Two: "2",
    Rank.Three: "3",
    Rank.Four: "4",
    Rank.Five: "5",
    Rank.Six: "6",
    Rank.Seven: "7",
    Rank.Eight: "8",
    Rank.Nine: "9",
    Rank.Ten: "10",
    Rank.Jack: "J",
    Rank.Queen: "Q",
    Rank.King: "K",
    Rank.Joker: "?",
}


@dataclass
class Card:
    suit: Suit
    rank: Rank

    @property
    def symbol(self):
        return f"{self.suit.symbol} {self.rank.symbol}"
