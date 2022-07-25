from typing import List, Union

from playthrough.models import GameConfig

from discord import CategoryChannel, Role, Interaction, TextChannel
from discord.utils import get


def get_game_completion_role(
    ctx: Interaction, game_config: GameConfig
) -> Union[Role, None]:
    """Utility function to get the completion role in the guild

    :param ctx: The Discord Interaction context.
    :param game_config: The game to get the completion role for.
    :return: The Role or None"""
    return get(ctx.guild.roles, id=int(game_config.completion_role_id))


def get_channel_in_guild(ctx: Interaction, channel_id: str) -> TextChannel:
    return get(ctx.guild.channels, id=int(channel_id))


async def get_game_categories(
    ctx: Interaction, game_config: "GameConfig"
) -> Union[List[CategoryChannel], None]:
    """Utility function to get the category configured for a certain game

    :param context: The Discord Context.
    :param game_config: The GameConfig to use to query
    :return: Categories in the server for the game or None"""
    return list(filter(lambda x: x.name == game_config.game.name, ctx.guild.categories))
