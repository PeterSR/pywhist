from dataclasses import dataclass

from .cards import Deck
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
        player_names = ("north", "east", "south", "west")

        # Create players (up to 4) based on preset player names
        players = [
            Player(id, name)
            for id, (_, name) in enumerate(zip(range(num_players), player_names))
        ]

        # Initially each player starts with an empty hand
        hands = {
            p: Deck.empty()
            for p in players
        }

        # Initally, we don't know who are partners.
        partners = {}

        return GameState(
            players=players,
            hands=hands,
            partner=partners,
        )

    def deal(self):
        deck = Deck.sorted()
        deck.shuffle()

        hand_size = 13
        assert len(self.state.players) == 4

        for p in self.state.players:
            for _ in range(hand_size):
                card = deck.cards.pop()
                self.state.hands[p].cards.append(card)
            self.state.hands[p].sort()

        self.state.kitty = deck

        for p, h in self.state.hands.items():
            print(f"Player: {p.name}")
            print(f"- {h}")
        print(self.state.kitty)

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

    game.deal()

    while not game.has_ended:
        player = game.current_player
        view = GameStateView(game.state, player)

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
