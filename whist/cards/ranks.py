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
    def name(self):
        return rank_name[self]

    @property
    def symbol(self):
        return rank_symbol[self]


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

ranks = (
    Rank.Ace, Rank.Two, Rank.Three,
    Rank.Four, Rank.Five, Rank.Six,
    Rank.Seven, Rank.Eight, Rank.Nine, Rank.Ten,
    Rank.Jack, Rank.Queen, Rank.King,
)
