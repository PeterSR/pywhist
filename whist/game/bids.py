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
