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



def create_default_players():
    num_players = 4
    player_names = ("north", "east", "south", "west")

    # Create players (up to 4) based on preset player names
    players = [
        Player(id, name)
        for id, (_, name)
        in enumerate(zip(range(num_players), player_names))
    ]

    return players