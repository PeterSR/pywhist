from dataclasses import dataclass
from typing import ClassVar

from .ranks import Rank, ranks
from .suits import Suit


@dataclass(order=True, frozen=True)
class Card:
    suit: Suit
    rank: Rank

    # Sentinel cards. The actual values are assigned below the class body so
    # that the @dataclass decorator doesn't treat them as fields.
    unknown: ClassVar["Card"]
    joker: ClassVar["Card"]

    @property
    def name(self) -> str:
        if self == Card.joker:
            return "joker"
        return f"{self.rank}-{self.suit}"

    @property
    def symbol(self) -> str:
        return card_symbol[self]


Card.unknown = Card(Suit.Unknown, Rank.Unknown)
Card.joker = Card(Suit.Unknown, Rank.Joker)


card_symbol: dict[Card, str] = {
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
    for rank, symbol in zip(ranks, symbols, strict=True):
        card = Card(suit, rank)
        card_symbol[card] = symbol
