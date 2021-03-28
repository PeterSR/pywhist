from dataclasses import dataclass
from collections import Counter

from .cards import Suit, Card, Deck
from .tableround import TableRound
from .gamestate import GameState, GameStateView, Player, Partners
from .game_actions import BaseAction, PlayAction
from .game_events import ActionTakenEvent, TrickTakenEvent
from .game_ai import RandomAI


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
        partners = Partners(players)
        partners.bisect(players[0], players[2])

        dealer = players[2]
        dealer_index = players.index(dealer)

        return GameState(
            dealer=dealer,
            players=players,
            hands=hands,
            partners=partners,
            turn=dealer_index,
        )

    def deal(self):
        deck = Deck.full_deck()
        deck.shuffle()

        hand_size = 13
        assert len(self.state.players) == 4

        card = None

        tableround = TableRound(self.state.dealer, self.state.players)

        for p in tableround:
            hand = self.state.hands[p]
            for _ in range(hand_size):
                card = deck.cards.pop()
                hand.give(card, sort=False)
            hand.sort()

        assert card is not None

        self.state.trump = card.suit

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

                # Determine winning team
                trick_winner = self._assign_trick(self.state.pile_play, card_scores)
                team_id = self.state.partners.team_id(trick_winner)

                # Add trick to list of tricks
                trick = pile.to_trick()
                trick_index = len(state.tricks)
                state.tricks.append(trick)
                state.trick_owner[trick_index] = team_id

                # Reset round
                state.round_reset()

                self.state.events.append(TrickTakenEvent(trick_winner, team_id, trick))

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

    def get_scoreboard(self):
        scores = Counter()

        for trick_index, team_id in self.state.trick_owner.items():
            scores[team_id] += 1

        scoreboard = {}

        for team_id, score in scores.items():
            members = tuple(self.state.partners.team_members(team_id))
            scoreboard[members] = score

        return scoreboard




# --- CLI ---


def display_board(view):
    for p, hand in view.other_players.items():
        print(f"{p.name:>6}: {hand}")

    print()
    for p in view.partners:
        print(f"Your partner: {p.name}")

    print()
    print(f"Trump: {view.trump.symbol}")
    print()

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
    import time

    # Interactive CLI game


    last_event_index = 0

    game = Game()

    controllers = []
    for player in game.state.players:
        view = GameStateView(game.state, player)
        ai = RandomAI(view)
        controllers.append(ai)

    my_view = controllers[0].game_state_view
    controllers[0] = "human"

    game.deal()

    while not game.has_ended:
        player = game.current_player
        controller = controllers[game.state.turn]

        if controller == "human":
            if len(game.state.events) > last_event_index:
                print()
                print("=== Events: ===")
                for event in game.state.events[last_event_index:]:
                    print("-", event)
                last_event_index = len(game.state.events)
                print()

            print()
            print(f"=== Turn: {player.name} ===")
            print()

            display_board(my_view)

            print("Actions:")
            actions = game.valid_actions(player)
            display_actions(actions)

            while True:
                s = input("> ")
                if s == "tricks":
                    print(game.state.tricks)
                    print(game.state.trick_owner)
                    continue

                action = parse_cli_action(s, actions)
                if game.is_valid_action(player, action):
                    result = game.take_action(player, action)
                    if result:
                        break
                else:
                    print("Invalid action.")
        else:
            actions = game.valid_actions(player)
            action = controller.pick_action(actions)
            game.take_action(player, action)

            print()
            print(f"=== Turn taken: {player.name} ===")
            print()

            display_board(my_view)

            if controllers[0] == "human":
                time.sleep(1)


    print("Tricks:")

    scoreboard = game.get_scoreboard()

    for team, s in scoreboard.items():
        team_str = ", ".join(p.name for p in team)
        print(f"{team_str:<13}: {s}")