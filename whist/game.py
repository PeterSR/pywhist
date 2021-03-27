from dataclasses import dataclass

from .cards import Suit, Card, Deck
from .gamestate import GameState, GameStateView, Player
from .game_actions import PlayAction, ActionTaken


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
            actions_taken=[],
            tricks=[],
        )

    def deal(self):
        deck = Deck.sorted()
        deck.shuffle()

        hand_size = 13
        assert len(self.state.players) == 4

        for p in self.state.players:
            hand = self.state.hands[p]
            for _ in range(hand_size):
                card = deck.cards.pop()
                hand.give(card, sort=False)
            hand.sort()

        self.state.kitty = Deck.from_deck(deck)

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
        pile = self.state.pile

        if len(pile) == 0:
            return [PlayAction(card) for card in hand]
        else:
            first_card = pile.cards[0]

            if first_card == Card.joker:
                suits_from_hand = hand
            else:
                suits_from_hand = [
                    card for card in hand
                    if card.suit is first_card.suit
                ]

            if len(suits_from_hand) > 0:
                return [PlayAction(card) for card in suits_from_hand]
            else:  # Renons
                return [PlayAction(card) for card in hand]

        return []

    def is_valid_action(self, player, action: PlayAction):
        if player != self.current_player:
            return False

        return action in self.valid_actions(player)

    def take_action(self, player, action):
        if isinstance(action, PlayAction):
            hand = self.state.hands[player]
            hand.take(action.card)

            pile = self.state.pile

            if len(pile) == 0:
                self.state.pile_suit = action.card.suit

            pile.give(action.card)

            if len(pile) == self.state.num_players:
                self.state.tricks.append(pile)
                self.state.pile = Deck.empty()
        else:
            raise ValueError(f"Invalid action: {action}")

        self.state.actions_taken.append(ActionTaken(player, action))
        self.state.turn = (self.state.turn + 1) % self.state.num_players

        return True

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
                result = game.take_action(player, action)
                if result:
                    break
            else:
                print("Invalid action.")
