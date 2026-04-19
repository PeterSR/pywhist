from ..util import OrderedEnum, auto


class Rank(OrderedEnum):
    Unknown = auto()
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
    Ace = auto()
    Joker = auto()

    @property
    def name(self) -> str:
        return rank_name[self]

    @property
    def symbol(self) -> str:
        return rank_symbol[self]

    @property
    def code(self) -> str:
        return rank_code[self]

    @classmethod
    def from_code(cls, code: str) -> "Rank":
        try:
            return code_rank[code]
        except KeyError as exc:
            raise ValueError(f"Unknown rank code: {code!r}") from exc


rank_name = {
    Rank.Unknown: "unknown",
    Rank.Ace: "ace",
    Rank.Two: "2",
    Rank.Three: "3",
    Rank.Four: "4",
    Rank.Five: "5",
    Rank.Six: "6",
    Rank.Seven: "7",
    Rank.Eight: "8",
    Rank.Nine: "9",
    Rank.Ten: "10",
    Rank.Jack: "jack",
    Rank.Queen: "queen",
    Rank.King: "king",
    Rank.Joker: "joker",
}

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

# Wire codes: single-char, JSON-safe. Differs from `symbol` where Ten is "10"
# and Joker is an emoji; wire codes are "T" and "*".
rank_code = {
    Rank.Unknown: "_",
    Rank.Two: "2",
    Rank.Three: "3",
    Rank.Four: "4",
    Rank.Five: "5",
    Rank.Six: "6",
    Rank.Seven: "7",
    Rank.Eight: "8",
    Rank.Nine: "9",
    Rank.Ten: "T",
    Rank.Jack: "J",
    Rank.Queen: "Q",
    Rank.King: "K",
    Rank.Ace: "A",
    Rank.Joker: "*",
}

code_rank = {code: rank for rank, code in rank_code.items()}

ranks = (
    Rank.Ace,
    Rank.Two,
    Rank.Three,
    Rank.Four,
    Rank.Five,
    Rank.Six,
    Rank.Seven,
    Rank.Eight,
    Rank.Nine,
    Rank.Ten,
    Rank.Jack,
    Rank.Queen,
    Rank.King,
)
