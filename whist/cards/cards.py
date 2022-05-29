from dataclasses import dataclass
from typing import List, Tuple

from .suits import Suit
from .ranks import Rank, ranks


@dataclass(order=True, frozen=True)
class Card:
    suit: Suit
    rank: Rank

    @property
    def name(self):
        if self == Card.joker:
            return "joker"
        else:
            return f"{self.rank}-{self.suit}"

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
