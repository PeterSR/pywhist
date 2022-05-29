from .match import Match
from .game.game import Game
from .game.state import GameStateView
from .game.player import create_default_players
from .game.actions import PlayAction, CallAction
from .game.ai import BaseAI, RandomAI


def display_board(view):
    for p, hand in view.other_players.items():
        print(f"{p.name:>6}: {hand}")

    print()
    if len(view.partners) == 0:
        print("(You have no partner)")
    for p in view.partners:
        print(f"Your partner: {p.name}")

    print()
    print(f"Trump:       {view.trump.symbol}")
    print(f"Partner Ace: {view.partner_ace.symbol}")
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
        elif isinstance(action, CallAction):
            s = f"Call {action.call.trump.symbol} trump with {action.call.partner_ace.symbol} ace"
        else:
            s = "?"
        print(f"{i:>2}: {s}")


if __name__ == "__main__":
    import time

    # Interactive CLI game


    game_speed = 1
    last_event_index = 0

    players = create_default_players()

    match = Match()
    match.state.scoreboard = {p.id: 0 for p in players}

    controllers = []
    for player in players:
        ai = RandomAI(None)
        controllers.append(ai)

    human_index = 0
    controllers[human_index] = "human"

    while not match.has_ended:
        match.new_game(players=players)

        game = match.current_game

        for player, controller in zip(players, controllers):
            if isinstance(controller, BaseAI):
                controller.game_state_view = GameStateView(game.state, player)

        my_view = GameStateView(game.state, players[human_index])

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

                    if s.startswith("speed:"):
                        _, x = s.split(":", 2)
                        try:
                            game_speed = float(x)
                        except ValueError:
                            pass
                        else:
                            print(f"Game speed changed to: {game_speed}")
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
                    time.sleep(game_speed)



        if len(game.state.events) > last_event_index:
            print()
            print("=== Events: ===")
            for event in game.state.events[last_event_index:]:
                print("-", event)
            last_event_index = len(game.state.events)
            print()

        print("Tricks:")

        scoreboard = game.get_scoreboard()

        for team, s in scoreboard.items():
            team_str = ", ".join(p.name for p in team)
            print(f"{team_str:<13}: {s}")