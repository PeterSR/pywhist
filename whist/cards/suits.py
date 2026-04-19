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

    @property
    def code(self) -> str:
        return suit_code[self]

    @classmethod
    def from_code(cls, code: str) -> "Suit":
        try:
            return code_suit[code]
        except KeyError as exc:
            raise ValueError(f"Unknown suit code: {code!r}") from exc


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

suit_code = {
    Suit.Unknown: "_",
    Suit.Club: "C",
    Suit.Diamond: "D",
    Suit.Heart: "H",
    Suit.Spade: "S",
}

code_suit = {code: suit for suit, code in suit_code.items()}

suits = (
    Suit.Club,
    Suit.Diamond,
    Suit.Heart,
    Suit.Spade,
)
