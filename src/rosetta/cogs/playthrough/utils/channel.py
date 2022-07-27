import logging
from typing import Union

from asgiref.sync import sync_to_async
from discord import HTTPException, Interaction, TextChannel as DiscordChannel
from django.core.files import File

from playthrough.models import Archive, Channel, GameConfig

from rosetta.cogs.playthrough.utils.discord import (
    get_channel_in_guild,
    get_game_categories,
)
from rosetta.utils.exporter import export_channel

logger = logging.getLogger(__name__)


async def archive_channel(ctx: Interaction, channel: Channel):
    """Utility to archive a playthrough channel for a certain game

    :param context: The Discord Context
    :param channel: The Channel to archive."""
    channel_in_guild = get_channel_in_guild(ctx, channel.id)
    if not channel_in_guild:
        return False
    try:
        exported_channel_file_path = export_channel(channel.id)
        exported_channel_file = File(
            file=open(exported_channel_file_path), name=exported_channel_file_path.name
        )
    except Exception as e:
        logger.error(e)
        await ctx.followup.send(
            (
                "Error occurred when archiving the channel, "
                "please check logs for more information. "
                "\nThe channel has not been deleted."
            ),
            ephemeral=True,
        )
        return False
    try:
        await sync_to_async(Archive.objects.create)(
            channel=channel, file=exported_channel_file
        )
        exported_channel_file.close()
        exported_channel_file_path.unlink()
    except Exception as e:
        print(e)
        logger.error(e)
        await ctx.followup.send(
            (
                "Error occurred when uploading the channel archive, "
                "please check logs for more information. "
                "\nThe channel has not been deleted."
            )
        )
        return False

    await channel_in_guild.delete()
    return True


async def create_channel(
    ctx: Interaction, game_config: GameConfig, name: str, permissions: dict
) -> Union[DiscordChannel, None]:
    """Creates a new playthrough channel in the guild.

    :param context: The Discord Context
    :param game_config: The game to create a channel for.
    :param name: The channel name.
    :param permissions: The permission overwrites for the channel.
    :param logger: The Logger to use to log things.
    """
    # Get category & channel name
    categories = await get_game_categories(ctx, game_config)
    for category in categories:
        try:
            channel = await ctx.guild.create_text_channel(
                name=name, category=category, overwrites=permissions
            )
            return channel
        except HTTPException:
            pass

    try:
        logger.warn(
            (
                f"Cap on categories for game `{game_config.game}` reached."
                " Creating a new one..."
            )
        )
        position = None
        if len(categories) > 0:
            position = categories[-1].position + 1
        category = await ctx.guild.create_category(
            name=game_config.game.name, position=position
        )
        logger.info(f"Created new category for {game_config.game}.")
        channel = await ctx.guild.create_text_channel(
            name=name, category=category, overwrites=permissions
        )
        logger.info(f"Created channel {name}.")
        return channel
    except (HTTPException) as e:
        logger.error(f"Error occurred when creating channel {name}", e)
        return None
