from ..util import OrderedEnum, auto


class Suit(OrderedEnum):
    Unknown = auto()
    Club = auto()
    Diamond = auto()
    Heart = auto()
    Spade = auto()

    @property
    def name(self) -> str:
        return suit_name[self]

    @property
    def symbol(self) -> str:
        return suit_symbol[self]


suit_name = {
    Suit.Unknown: "unknown",
    Suit.Club: "club",
    Suit.Diamond: "diamond",
    Suit.Heart: "heart",
    Suit.Spade: "spade",
}

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
