from dataclasses import dataclass


PlayerID = int


@dataclass(frozen=True)
class Player:
    id: PlayerID
    name: str

    def serialize(self):
        return {
            "id": self.id,
            "name": self.name,
        }