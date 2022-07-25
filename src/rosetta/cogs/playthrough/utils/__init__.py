from playthrough.models import GameConfig


def get_instructions(game_config: GameConfig) -> str:
    """Get the instructions message.

    :game_config: The game to get a message for.
    :return: The instructions message."""
    return (
        f"Welcome to your `{game_config.game}` playthrough channel!\n"
        f"When you have finished the game, type `/finished {game_config.game.name}` "
        "and this channel will be archived. "
        "If you wish to drop the game or stop your playthrough for a prolonged period of time "
        f"please use `/drop {game_config.game.name}` and your channel will be archived. "
        f" When you're back, you can click the same button you did just now to resume playing!\n"
        "Finally, do note that you have 'Manage Channel' permissions if you wish to change the channel "
        "name or who has permission to access it.\n"
        "You can find previous archives of your channel here: https://genki.rainm.io/"
    )
