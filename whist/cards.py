from dataclasses import dataclass
from enum import Enum, auto
from typing import List


class Suit(Enum):
    Unknown = auto()
    Club = auto()
    Diamond = auto()
    Heart = auto()
    Spade = auto()

    @property
    def symbol(self):
        return suit_symbol[self]


suit_symbol = {
    Suit.Unknown: "_",
    Suit.Club: "♣",
    Suit.Diamond: "♦",
    Suit.Heart: "♥",
    Suit.Spade: "♠",
}

suits = (
    Suit.Club,
    Suit.Diamond,
    Suit.Heart,
    Suit.Spade,
)


class Rank(Enum):
    Unknown = auto()
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
    Rank.Unknown: "_",
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
    Rank.Joker: "🃏",
}

ranks = (
    Rank.Ace, Rank.Two, Rank.Three,
    Rank.Four, Rank.Five, Rank.Six,
    Rank.Seven, Rank.Eight, Rank.Nine, Rank.Ten,
    Rank.Jack, Rank.Queen, Rank.King,
)


@dataclass(frozen=True)
class Card:
    suit: Suit
    rank: Rank

    @property
    def symbol(self):
        return card_symbol[self]


Card.unknown = Card(Suit.Unknown, Rank.Unknown)
Card.joker = Card(Suit.Unknown, Rank.Joker)


card_symbol = {
    Card.unknown: "🂠",
    Card.joker: "🃏",
}

card_symbol_unicode = {
    Suit.Heart: "🂱 🂲 🂳 🂴 🂵 🂶 🂷 🂸 🂹 🂺 🂻 🂽 🂾",
    Suit.Spade: "🂡 🂢 🂣 🂤 🂥 🂦 🂧 🂨 🂩 🂪 🂫 🂭 🂮",
    Suit.Diamond: "🃁 🃂 🃃 🃄 🃅 🃆 🃇 🃈 🃉 🃊 🃋 🃍 🃎",
    Suit.Club: "🃑 🃒 🃓 🃔 🃕 🃖 🃗 🃘 🃙 🃚 🃛 🃝 🃞",
}

for suit, line in card_symbol_unicode.items():
    symbols = line.split(" ")
    for rank, symbol in zip(ranks, symbols):
        card = Card(suit, rank)
        card_symbol[card] = symbol


@dataclass
class Deck:
    cards: List[Card]

    @staticmethod
    def empty():
        return Deck([])

    @staticmethod
    def sorted(num_jokers=3):
        deck = Deck.empty()

        for suit in suits:
            for rank in ranks:
                deck.cards.append(Card(suit, rank))

        for _ in range(num_jokers):
            deck.cards.append(Card.joker)

        return deck
