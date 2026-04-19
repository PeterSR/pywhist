from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from ..cards import Card, Trick
from .actions import BaseAction, action_from_dict
from .partners import TeamID
from .phase import Phase
from .player import Player


class BaseEvent:
    def to_dict(self) -> dict[str, Any]:
        raise NotImplementedError


@dataclass(frozen=True)
class ActionTakenEvent(BaseEvent):
    player: Player
    action: BaseAction

    def __str__(self) -> str:
        return f"Player {self.player.name}: {self.action}"

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": "action_taken",
            "player": self.player.to_dict(),
            "action": self.action.to_dict(),
        }

    @classmethod
    def from_dict(cls, d: Mapping[str, Any]) -> "ActionTakenEvent":
        return cls(
            player=Player.from_dict(d["player"]),
            action=action_from_dict(d["action"]),
        )


@dataclass(frozen=True)
class TrickTakenEvent(BaseEvent):
    player: Player
    team_id: TeamID
    trick: Trick

    def __str__(self) -> str:
        trick_symbols = tuple(card.symbol for card in self.trick)
        return f"Player {self.player.name} took {trick_symbols}"

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": "trick_taken",
            "player": self.player.to_dict(),
            "team_id": int(self.team_id),
            "trick": [c.to_dict() for c in self.trick],
        }

    @classmethod
    def from_dict(cls, d: Mapping[str, Any]) -> "TrickTakenEvent":
        cards_list = [Card.from_dict(c) for c in d["trick"]]
        if len(cards_list) != 4:
            raise ValueError(f"Expected 4 cards in trick, got {len(cards_list)}")
        trick: Trick = (cards_list[0], cards_list[1], cards_list[2], cards_list[3])
        return cls(
            player=Player.from_dict(d["player"]),
            team_id=TeamID(int(d["team_id"])),
            trick=trick,
        )


@dataclass(frozen=True)
class PhaseTransitionEvent(BaseEvent):
    from_phase: Phase
    to_phase: Phase

    def __str__(self) -> str:
        return f"Phase: {self.from_phase.value} → {self.to_phase.value}"

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": "phase_transition",
            "from_phase": self.from_phase.value,
            "to_phase": self.to_phase.value,
        }

    @classmethod
    def from_dict(cls, d: Mapping[str, Any]) -> "PhaseTransitionEvent":
        return cls(
            from_phase=Phase(d["from_phase"]),
            to_phase=Phase(d["to_phase"]),
        )


_EVENT_TAGS: dict[str, type[BaseEvent]] = {
    "action_taken": ActionTakenEvent,
    "trick_taken": TrickTakenEvent,
    "phase_transition": PhaseTransitionEvent,
}


def event_from_dict(d: Mapping[str, Any]) -> BaseEvent:
    tag = d["type"]
    cls = _EVENT_TAGS.get(tag)
    if cls is None:
        raise ValueError(f"Unknown event tag: {tag!r}")
    return cls.from_dict(d)  # type: ignore[attr-defined,no-any-return]
