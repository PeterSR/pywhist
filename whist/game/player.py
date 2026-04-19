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


def create_default_players() -> list[Player]:
    player_names = ("north", "east", "south", "west")
    return [Player(idx, name) for idx, name in enumerate(player_names)]
