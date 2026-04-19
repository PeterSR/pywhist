from dataclasses import dataclass

from ..cards import Suit
from ..util import OrderedEnum, auto


class BidAddition(OrderedEnum):
    Good = auto()
    Half = auto()
    Vip = auto()
    Sans = auto()


class BidNolo(OrderedEnum):
    Sol = auto()
    RenSol = auto()
    Bordlaegger = auto()
    RenBordlaegger = auto()


@dataclass
class Bid:
    amount: int
    addition: BidAddition
    nolo: BidNolo


@dataclass
class Call:
    trump: Suit = None
    partner_ace: Suit = None

    def to_dict(self):
        trump = self.trump if self.trump is not None else Suit.Unknown
        partner_ace = self.partner_ace if self.partner_ace is not None else Suit.Unknown
        return {"trump": trump.code, "partner_ace": partner_ace.code}

    @classmethod
    def from_dict(cls, d):
        return cls(
            trump=Suit.from_code(d["trump"]),
            partner_ace=Suit.from_code(d["partner_ace"]),
        )
