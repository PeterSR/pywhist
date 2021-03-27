from dataclasses import dataclass

from .gamestate import GameState, GameStateView, Player


@dataclass
class Game:
    state: GameState = None

    def __post_init__(self):
        if self.state is None:
            self.state = self.initial_state()

    @staticmethod
    def initial_state(**settings):
        num_players = settings.get("num_players", 4)
        players = []

        return GameState(
            players=players,
        )

    @property
    def has_ended(self):
        return False

    @property
    def current_player(self):
        return self.state.players[self.state.turn]

    def valid_actions(self):
        return []

    def is_valid_action(self, player, action):
        if player != self.current_player:
            return False

        return action in self.valid_actions()



# --- CLI ---

def parse_cli_action(action):
    return True


def display_actions(actions):
    pass


if __name__ == "__main__":
    # Interactive CLI game

    game = Game()

    while not game.has_ended:
        player = game.current_player
        view = GameStateView(game.state)

        print(f"Turn: {player}")
        print(f"Pile: {view.pile}")
        print(f"Hand: {view.hand}")
        print("Actions:")
        display_actions(view.actions)

        while True:
            action = input("> ")
            action = parse_cli_action(action)
            if game.is_valid_action(player, action):
                game.take_action(player, action)
            else:
                print("Invalid action.")
