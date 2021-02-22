from dataclasses import dataclass

from .gamestate import GameState, GameStateView


@dataclass
class Game:
    state: GameState

    @property
    def has_ended(self):
        return False

    @property
    def current_player(self):
        return "North"

    def valid_actions(self):
        return []

    def is_valid_action(self, player, action):
        if player != self.current_player:
            return False

        return action in self.valid_actions()



# --- CLI ---

def parse_cli_action(action):
    return True


if __name__ == "__main__":
    # Interactive CLI game

    game = Game()

    while not game.has_ended:
        player = game.current_player
        view = GameStateView(game.state)

        print(f"Turn: {player}")
        print(f"Pile: {view.pile}")
        print(f"Hand: {view.hand}")

        while True:
            action = input("> ")
            action = parse_cli_action(action)
            if game.is_valid_action(player, action):
                game.take_action(player, action)
            else:
                print("Invalid action.")
