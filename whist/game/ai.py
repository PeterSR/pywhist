import random

from .state import GameStateView


class BaseAI:

    def __init__(self, game_state_view: GameStateView):
        self.game_state_view = game_state_view

    def pick_action(self, actions):
        raise NotImplementedError()


class RandomAI(BaseAI):

    def pick_action(self, actions):
        action, = random.sample(actions, 1)
        return action
