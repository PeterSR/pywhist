from __future__ import annotations

from dataclasses import dataclass
from collections import Counter
from itertools import product

from ..cards import Suit, Rank, Card, Deck, suits
from .tableround import TableRound
from .state import GameState, Player, Partners
from .actions import BaseAction, PlayAction, CallAction
from .bids import Call
from .events import ActionTakenEvent, TrickTakenEvent


@dataclass
class Game:
    """
    Represents the game logic for a single game (dealing, bidding and 13 tricks)
    """

    state: GameState = None
    variant: str = "esmakker"

    def __post_init__(self):
        if self.state is None:
            self.state = self.initial_state()

    def initial_state(self, **settings):
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

        if self.variant == "classic":
            partners.bisect(players[0], players[2])

        dealer = players[3]
        dealer_index = players.index(dealer)

        return GameState(
            dealer=dealer,
            players=players,
            hands=hands,
            partners=partners,
            turn=dealer_index,
        )

    def deal(self):
        self.state.phase = "dealing"

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

        if self.variant == "classic":
            assert card is not None
            self.state.trump = card.suit

        self.state.kitty = Deck.from_deck(deck)

        self.state.phase = "calling"

        caller = next(iter(TableRound(self.state.dealer, self.state.players)))
        self.bid_winner = caller
        self.state.turn = self.state.players.index(self.bid_winner)

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

        if self.state.phase == "calling":
            calls = [
                CallAction(Call(trump, partner_ace))
                for trump, partner_ace in product(suits, suits)
            ]

            return calls

        elif self.state.phase == "playing":
            hand = self.state.hands[player]
            pile = self.state.pile

            if len(pile) == 0:
                return [PlayAction(card) for card in hand]
            else:
                first_card = pile.cards[0]

                if first_card == Card.joker:
                    suits_from_hand = hand
                else:
                    if first_card.suit == self.state.partner_ace:
                        partner_ace = Card(self.state.partner_ace, Rank.Ace)
                        if partner_ace in hand:
                            return [PlayAction(partner_ace)]

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

        if isinstance(action, CallAction):
            self.state.trump = action.call.trump
            self.state.partner_ace = action.call.partner_ace

            partner_ace_player = self._determine_partner_ace_player()
            self.state.partners.bisect(self.bid_winner, partner_ace_player)

            self.state.phase = "playing"
        elif isinstance(action, PlayAction):
            state = self.state
            hand = state.hands[player]
            hand.take(action.card)

            pile = state.pile

            if len(pile) == 0:
                state.pile_suit = action.card.suit

            pile.give(action.card)
            state.pile_play.append(player)

            # If the partner ace was played, assign partners
            partner_ace = Card(self.state.partner_ace, Rank.Ace)
            if action.card == partner_ace:
                self.state.partner_ace_revealed = True

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

    def _determine_partner_ace_player(self):
        partner_ace_card = Card(self.state.partner_ace, Rank.Ace)

        for player in self.state.players:
            hand = self.state.hands[player]
            for card in hand:
                if card == partner_ace_card:
                    return player

        return None



    def get_scoreboard(self):
        scores = Counter()

        for trick_index, team_id in self.state.trick_owner.items():
            scores[team_id] += 1

        scoreboard = {}

        for team_id, score in scores.items():
            members = tuple(self.state.partners.team_members(team_id))
            scoreboard[members] = score

        return scoreboard
