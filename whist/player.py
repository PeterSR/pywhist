from dataclasses import dataclass


PlayerID = int


@dataclass(frozen=True)
class Player:
    id: PlayerID
    name: str
