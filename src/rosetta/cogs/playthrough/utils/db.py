from typing import Union

from asgiref.sync import sync_to_async
from playthrough.models import Channel, Game, GameConfig, User, MetaRoleConfig, Guild

from discord.utils import get

import discord


async def get_game_config(
    context: discord.Interaction, game: str
) -> "Union[GameConfig,None]":
    """Utility function to check if the current guild has a certain game configured

    :param context: The Discord Context.
    :param game: The game to check for.
    :return: Game Configuration or None"""
    return await sync_to_async(GameConfig.get_by_game_alias)(
        game, str(context.guild_id)
    )


async def get_all_games_per_guild() -> dict[str, GameConfig]:
    def _query():
        ret = {}
        guilds = list(Guild.objects.prefetch_related("games", "games__game").all())

        for guild in guilds:
            game_configs = list(
                GameConfig.objects.select_related("game").filter(
                    guild__id=str(guild.id)
                )
            )
            ret[int(guild.id)] = game_configs

        return ret

    return await sync_to_async(_query)()


async def get_playable_games(guild_id: int) -> list[GameConfig]:
    def _query():
        return list(
            GameConfig.objects.select_related("game").filter(
                guild__id=str(guild_id), playable=True
            )
        )

    return await sync_to_async(_query)()


async def get_meta_roles(game_config: GameConfig) -> list[MetaRoleConfig]:
    def _query():
        return list(game_config.meta_roles.all())

    return await sync_to_async(_query)()


async def get_existing_channel(
    ctx: discord.Interaction, game: Game
) -> Union[Channel, None]:
    """Utility function to get the existing channel for a user for a game.

    :param ctx: The Discord Interaction context.
    :param game: The game to get the channel for.
    :return: Existing Channel in the guild for a certain game or None"""
    existing_channel = await sync_to_async(
        Channel.objects.filter(owner_id=ctx.user.id, game=game)
        .prefetch_related("archives")
        .first
    )()
    if existing_channel is not None:
        # If the user supposedly has an existing channel
        # if it's not in the guild and has no archives, remove from the DB
        channel_in_guild = get(ctx.guild.channels, id=int(existing_channel.id))
        if channel_in_guild is None and len(existing_channel.archives.all()) == 0:
            await sync_to_async(existing_channel.delete)()
        else:  # Otherwise, user already has a channel!
            return existing_channel
    return None


async def create_channel_in_db(
    ctx: discord.Interaction,
    game_config: GameConfig,
    channel_id: str,
    finished: bool = False,
) -> Channel:
    """Utility function to create a channel in the database

    :param context: The Discord Context.
    :param game_config: The GameConfig to use for extra info.
    :param finished: Whether or not the channel is finished.
    :return: The Channel that was created"""
    owner = (await sync_to_async(User.objects.get_or_create)(id=ctx.user.id))[0]
    return await sync_to_async(Channel.objects.create)(
        id=channel_id,
        owner=owner,
        guild_id=ctx.guild.id,
        game=game_config.game,
        finished=finished,
    )
