from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from itertools import product
from random import Random
from typing import Any

from ..cards import Card, Deck, Rank, Suit, suits
from ..errors import IllegalAction, IllegalPhase
from .actions import BaseAction, CallAction, PlayAction
from .bids import Call
from .partners import Partners, TeamID
from .phase import Phase
from .player import Player, create_default_players
from .reducer import apply
from .ruleset import Ruleset
from .state import GameState
from .tableround import TableRound


@dataclass
class Game:
    """Ergonomic mutating wrapper over the pure reducer.

    `Game` keeps a single `GameState` that it replaces atomically on each
    `take_action`. The underlying transition is computed by `reducer.apply`,
    so test code and RL training can skip the wrapper and call `apply`
    directly for deterministic replay.
    """

    state: GameState | None = None
    ruleset: Ruleset | None = None
    seed: int | None = None
    _rng: Random = field(default_factory=Random, repr=False, compare=False)

    def __post_init__(self) -> None:
        if self.ruleset is None:
            self.ruleset = Ruleset.petersmakker()
        if self.seed is not None:
            self._rng = Random(self.seed)
        if self.state is None:
            self.state = self.initial_state()

    def initial_state(self, **settings: Any) -> GameState:
        players_list = settings.get("players")

        if players_list is None:
            players_list = create_default_players()

        players: tuple[Player, ...] = tuple(players_list)
        hands = {p: Deck.empty() for p in players}
        partners = Partners(list(players))

        dealer_index = int(settings.get("dealer_index", 0))
        dealer = players[dealer_index]

        turn = int(settings.get("turn", 0))

        return GameState(
            players=players,
            dealer=dealer,
            hands=hands,
            partners=partners,
            turn=turn,
        )

    def deal(self) -> None:
        assert self.state is not None

        deck = Deck.full_deck()
        deck.shuffle(rng=self._rng)

        hand_size = 13
        if len(self.state.players) != 4:
            raise IllegalAction("deal expects exactly 4 players")

        assert self.state.dealer is not None
        tableround = TableRound(self.state.dealer, list(self.state.players))

        new_hands: dict[Player, Deck] = {}
        deck_cards = list(deck.cards)
        for p in tableround:
            cards_for_p = [deck_cards.pop() for _ in range(hand_size)]
            hand = Deck(cards_for_p)
            hand.sort()
            new_hands[p] = hand

        kitty = Deck(deck_cards)

        caller = next(iter(TableRound(self.state.dealer, list(self.state.players))))
        turn = self.state.players.index(caller)

        self.state = self.state.replace(
            phase=Phase.CALLING,
            hands=new_hands,
            kitty=kitty,
            bid_winner=caller,
            turn=turn,
        )

    @property
    def has_ended(self) -> bool:
        assert self.state is not None
        hand_size = 13
        return len(self.state.tricks) >= hand_size

    @property
    def current_player(self) -> Player:
        assert self.state is not None
        return self.state.current_player

    @property
    def bid_winner(self) -> Player | None:
        """Kept for back-compat — `state.bid_winner` is the source of truth."""
        assert self.state is not None
        return self.state.bid_winner

    def valid_actions(self, player: Player) -> list[BaseAction]:
        assert self.state is not None
        state = self.state

        if player != self.current_player:
            return []

        if state.phase == Phase.CALLING:
            return [
                CallAction(Call(trump, partner_ace)) for trump, partner_ace in product(suits, suits)
            ]

        if state.phase == Phase.PLAYING:
            hand = state.hands[player]
            pile = state.pile

            if len(pile) == 0:
                return [PlayAction(card) for card in hand]

            first_card = pile.cards[0]

            if first_card == Card.joker:
                suits_from_hand = list(hand)
            else:
                if first_card.suit == state.partner_ace:
                    partner_ace = Card(state.partner_ace, Rank.Ace)
                    if partner_ace in hand:
                        return [PlayAction(partner_ace)]

                suits_from_hand = [card for card in hand if card.suit is first_card.suit]

            if len(suits_from_hand) > 0:
                return [PlayAction(card) for card in suits_from_hand]
            # Renons
            return [PlayAction(card) for card in hand]

        raise IllegalPhase(f"valid_actions: no dispatch for phase {state.phase!r}")

    def is_valid_action(self, player: Player, action: BaseAction) -> bool:
        if player != self.current_player:
            return False
        return action in self.valid_actions(player)

    def take_action(self, player: Player, action: BaseAction) -> bool:
        assert self.state is not None
        if not isinstance(action, BaseAction):
            raise TypeError(f"Not an action: {action}")

        new_state, _events = apply(self.state, action, rng=self._rng)
        self.state = new_state
        return True

    def get_scoreboard(self) -> dict[tuple[Player, ...], int]:
        assert self.state is not None
        assert self.state.partners is not None

        scores: Counter[TeamID] = Counter()
        for team_id in self.state.trick_owner.values():
            scores[team_id] += 1

        scoreboard: dict[tuple[Player, ...], int] = {}
        for team_id, score in scores.items():
            members = tuple(self.state.partners.team_members(team_id))
            scoreboard[members] = score

        return scoreboard

    # Used by `take_action` — kept on the class so phase-6 can extend without
    # reshuffling call sites. The reducer re-implements the same logic.
    def _determine_partner_ace_player(self) -> Player | None:
        assert self.state is not None
        partner_ace_card = Card(self.state.partner_ace, Rank.Ace)
        for player in self.state.players:
            hand = self.state.hands[player]
            for card in hand:
                if card == partner_ace_card:
                    return player
        return None

    # Kept for CLI rendering until phase 11. The reducer owns scoring
    # internally via `reducer._score_pile`.
    def _score_pile(self, pile: Deck) -> list[int]:
        assert self.state is not None
        if len(pile) == 0:
            return []

        first_card = pile.cards[0]
        valid_trump = self.state.trump is not Suit.Unknown

        card_scores: list[int] = []
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

    def _assign_trick(self, pile_play: list[Player], scores: list[int]) -> Player:
        _, winner = max(zip(scores, pile_play, strict=True))
        return winner
