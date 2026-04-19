from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

PlayerID = int


@dataclass(frozen=True)
class Player:
    id: PlayerID
    name: str

    def to_dict(self) -> dict[str, Any]:
        return {"id": self.id, "name": self.name}

    @classmethod
    def from_dict(cls, d: Mapping[str, Any]) -> "Player":
        return cls(id=int(d["id"]), name=str(d["name"]))

    # Back-compat alias retained while older callers still exist.
    def serialize(self) -> dict[str, Any]:
        return self.to_dict()


def create_default_players() -> list[Player]:
    player_names = ("north", "east", "south", "west")
    return [Player(idx, name) for idx, name in enumerate(player_names)]
