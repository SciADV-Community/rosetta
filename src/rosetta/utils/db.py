from typing import Union

import discord
from asgiref.sync import sync_to_async
from discord.utils import get

from playthrough.models import Channel, Game, GameConfig, Guild, MetaRoleConfig, User


@sync_to_async
def get_or_create_guild(guild: discord.Guild) -> Guild:
    """Get or create a Guild DB object from a Guild Discord object.

    :param guild: the Discord Guild object.
    :return: a DB Guild object with creation info.
    """
    res = Guild.objects.get_or_create(id=str(guild.id))
    res[0].name = guild.name
    res[0].save()
    return res


@sync_to_async
def get_user_from_author(author: discord.User) -> User:
    """Get a DB User object from a Discord User object.

    :param author: the Discord User object.
    :return: a DB User object.
    """
    return User.objects.filter(id=author.id).first()


@sync_to_async
def get_game_config(context: discord.Interaction, game: str) -> Union[GameConfig, None]:
    """Utility function to check if the current guild has a certain game configured

    :param context: The Discord Context.
    :param game: The game to check for.
    :return: Game Configuration or None"""
    return GameConfig.get_by_game_alias(game, str(context.guild_id))


@sync_to_async
def get_all_games_per_guild() -> dict[str, list[GameConfig]]:
    """Get all the GameConfigs for every Guild the bot is in.

    :return: A dictionary keyed by Guild ID (int) and valued with a list of GameConfigs.
    """
    ret = {}
    guilds = list(Guild.objects.prefetch_related("games", "games__game").all())

    for guild in guilds:
        game_configs = list(
            GameConfig.objects.select_related("game").filter(guild__id=str(guild.id))
        )
        ret[int(guild.id)] = game_configs

    return ret


@sync_to_async
def get_playable_games(guild_id: Union[int, str]) -> list[GameConfig]:
    """Get all the playable games in a given Guild.

    :param guild_id: the ID of the guild to fetch for.
    :return: A list of GameConfig objects for the guild.
    """
    return list(
        GameConfig.objects.select_related("game").filter(
            guild__id=str(guild_id), playable=True
        )
    )


@sync_to_async
def get_meta_roles(game_config: GameConfig) -> list[MetaRoleConfig]:
    """Utility function to get the Meta Roles for a given GameConfig.
    Mostly useful when they haven't been pre-fetched.

    :param game_config: the GameConfig to get the MetaRoleConfigs from.
    :return: The MetaRoleConfigs for the GameConfig.
    """
    assert game_config
    return list(game_config.meta_roles.all())


@sync_to_async
def get_existing_channel(ctx: discord.Interaction, game: Game) -> Union[Channel, None]:
    """Utility function to get the existing channel for a user for a game.

    :param ctx: The Discord Interaction context.
    :param game: The game to get the channel for.
    :return: Existing Channel in the guild for a certain game or None."""
    existing_channel = (
        Channel.objects.filter(owner_id=ctx.user.id, game=game)
        .prefetch_related("archives")
        .first()
    )
    if existing_channel is not None:
        # If the user supposedly has an existing channel
        # if it's not in the guild and has no archives, remove from the DB
        channel_in_guild = get(ctx.guild.channels, id=int(existing_channel.id))
        if channel_in_guild is None and len(existing_channel.archives.all()) == 0:
            existing_channel.delete()
        else:  # Otherwise, user already has a channel!
            return existing_channel
    return None


@sync_to_async
def create_channel_in_db(
    ctx: discord.Interaction,
    game_config: GameConfig,
    channel_id: str,
    finished: bool = False,
) -> Channel:
    """Utility function to create a channel in the database.

    :param ctx: The Discord Context.
    :param game_config: The GameConfig to use for extra info.
    :param channel_id: the ID of the channel to create in the db.
    :param finished: Whether or not the channel is finished.
    :return: The Channel that was created."""
    owner = User.objects.get_or_create(id=ctx.user.id)[0]
    return Channel.objects.create(
        id=channel_id,
        owner=owner,
        guild_id=ctx.guild.id,
        game=game_config.game,
        finished=finished,
    )


@sync_to_async
def update_channel_id(channel: Channel, new_id: int):
    """Update a Chanel's ID value. For instance when the user creates a resume channel.

    :param channel: the Channel to update.
    :param new_id: the new ID to update to.
    """
    channel.update_id(new_id)
