from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from ..cards import Card
from .bids import Call


class BaseAction:
    """Base class for game actions."""

    def to_dict(self) -> dict[str, Any]:
        raise NotImplementedError


@dataclass(frozen=True)
class PlayAction(BaseAction):
    card: Card

    def __str__(self) -> str:
        return f"Played {self.card.symbol}"

    def to_dict(self) -> dict[str, Any]:
        return {"type": "play", "card": self.card.to_dict()}

    @classmethod
    def from_dict(cls, d: Mapping[str, Any]) -> "PlayAction":
        return cls(Card.from_dict(d["card"]))


@dataclass(frozen=True)
class CallAction(BaseAction):
    call: Call

    def __str__(self) -> str:
        return f"Called {self.call.trump.symbol} trump with {self.call.partner_ace.symbol} ace"

    def to_dict(self) -> dict[str, Any]:
        # Call lives in bids.py (excluded from mypy pending phase-6 rewrite),
        # so its methods are untyped from mypy's perspective.
        return {"type": "call", "call": self.call.to_dict()}  # type: ignore[no-untyped-call]

    @classmethod
    def from_dict(cls, d: Mapping[str, Any]) -> "CallAction":
        return cls(Call.from_dict(d["call"]))  # type: ignore[no-untyped-call]


_ACTION_TAGS: dict[str, type[BaseAction]] = {"play": PlayAction, "call": CallAction}


def action_from_dict(d: Mapping[str, Any]) -> BaseAction:
    tag = d["type"]
    cls = _ACTION_TAGS.get(tag)
    if cls is None:
        raise ValueError(f"Unknown action tag: {tag!r}")
    return cls.from_dict(d)  # type: ignore[attr-defined,no-any-return]
