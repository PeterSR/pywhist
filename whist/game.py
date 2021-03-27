from dataclasses import dataclass

from .cards import Suit, Card, Deck
from .gamestate import GameState, GameStateView, Player
from .game_actions import BaseAction, PlayAction
from .game_events import ActionTakenEvent, TrickTakenEvent


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
            for id, (_, name)
            in enumerate(zip(range(num_players), player_names))
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
        deck = Deck.full_deck()
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
        hand_size = 13
        return len(self.state.tricks) >= hand_size

    @property
    def current_player(self):
        return self.state.current_player

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
        if not isinstance(action, BaseAction):
            raise ValueError(f"Not an action: {action}")

        self.state.events.append(ActionTakenEvent(player, action))

        if isinstance(action, PlayAction):
            state = self.state
            hand = state.hands[player]
            hand.take(action.card)

            pile = state.pile

            if len(pile) == 0:
                state.pile_suit = action.card.suit

            pile.give(action.card)
            state.pile_play.append(player)

            if len(pile) == state.num_players:
                # Score trick
                card_scores = self._score_pile(pile)
                trick_winner = self._assign_trick(self.state.pile_play, card_scores)
                trick = pile.to_trick()
                trick_index = len(state.tricks)
                state.tricks.append(trick)
                state.trick_owner[trick_index] = trick_winner
                state.pile = Deck.empty_pile()

                self.state.events.append(TrickTakenEvent(player, trick))

                state.turn = state.players.index(trick_winner)

            else:
                state.turn = (state.turn + 1) % state.num_players
        else:
            raise ValueError(f"Invalid action: {action}")

        return True

    def _score_pile(self, pile) -> list:
        if len(pile) == 0:
            return {}

        first_card = pile.cards[0]
        valid_trump = self.state.trump is not Suit.Unknown

        card_scores = []
        for card in pile:
            value = card.rank.value
            if valid_trump and card.suit is self.state.trump:
                value += 100
            elif card.suit is not first_card.suit:
                value -= 100
            card_scores.append(value)

        if first_card == Card.joker:
            card_scores[0] += 1000

        return card_scores

    def _assign_trick(self, pile_play, scores):
        _, winner = max(zip(scores, pile_play))
        return winner




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


    last_event_index = 0

    game = Game()

    game.deal()

    while not game.has_ended:
        player = game.current_player
        view = GameStateView(game.state, player)

        print("=== Events: ===")
        if len(game.state.events) > last_event_index:
            for event in game.state.events[last_event_index:]:
                print(event)
            last_event_index = len(game.state.events)

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
