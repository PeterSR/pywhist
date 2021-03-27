from dataclasses import dataclass

from .cards import Deck
from .gamestate import GameState, GameStateView, Player
from .game_actions import PlayAction


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
                self.state.hands[p].give(card, sort=False)
            self.state.hands[p].sort()

        self.state.kitty = deck

    @property
    def has_ended(self):
        return False

    @property
    def current_player(self):
        return self.state.players[self.state.turn]

    def valid_actions(self, player):
        if player != self.current_player:
            return []

        hand = self.state.hands[player]

        if len(self.state.pile) == 0:
            return [PlayAction(card) for card in hand]

        return []

    def is_valid_action(self, player, action: PlayAction):
        if player != self.current_player:
            return False

        return action in self.valid_actions(player)


# --- CLI ---


def display_board(view):
    for p, hand in view.other_players.items():
        print(f"{p.name:>6}: {hand}")

    print()
    print(f"Pile: {view.pile}")
    print()
    print(f"Your hand: {view.hand}")
    print()


def parse_cli_action(s, actions):
    try:
        index = int(s)
    except ValueError:
        return None

    try:
        return actions[index]
    except IndexError:
        return None


def display_actions(actions):
    for i, action in enumerate(actions):
        if isinstance(action, PlayAction):
            s = action.card.symbol
        else:
            s = "?"
        print(f"{i:>2}: {s}")


if __name__ == "__main__":
    # Interactive CLI game

    game = Game()

    game.deal()

    while not game.has_ended:
        player = game.current_player
        view = GameStateView(game.state, player)

        print(f"=== Turn: {player.name} ===")
        print()

        display_board(view)

        print("Actions:")
        actions = game.valid_actions(player)
        display_actions(actions)

        while True:
            s = input("> ")
            action = parse_cli_action(s, actions)
            if game.is_valid_action(player, action):
                game.take_action(player, action)
            else:
                print("Invalid action.")
