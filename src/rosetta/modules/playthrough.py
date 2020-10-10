import logging
from typing import TYPE_CHECKING

from asgiref.sync import sync_to_async
from discord import HTTPException, PermissionOverwrite
from django.core.files import File
from discord.ext.commands import Cog, command
from discord.utils import get
from playthrough.models import Channel, Game, GameConfig, User, Archive
from rosetta.utils.exporter import export_channel
from rosetta.config import PREFIX

if TYPE_CHECKING:
    from typing import Union, List
    from discord import CategoryChannel as DiscordCategory
    from discord import TextChannel as DiscordChannel
    from discord import Role
    from discord.ext.commands import Context


logger = logging.getLogger(__name__)


async def get_existing_channel(
    context: 'Context', game: 'Game'
) -> 'Union[Channel,None]':
    """Utility function to get the existing channel for a user for a game.

    :param context: The Discord Context.
    :param game: The game to get the channel for.
    :return: Existing Channel in the guild for a certain game or None"""
    existing_channel = await sync_to_async(Channel.objects.filter(
        owner_id=context.author.id, game=game
    ).first)()
    if existing_channel is not None:
        archive = await sync_to_async(Archive.objects.filter(
            channel=existing_channel
        ).first)()
        # If the user supposedly has an existing channel
        # if it's not in the guild, remove from the DB
        channel_in_guild = get(context.guild.channels, id=int(existing_channel.id))
        if channel_in_guild is None and archive is None:
            await sync_to_async(existing_channel.delete)()
        else:  # Otherwise, user already has a channel!
            return existing_channel
    return None


async def get_game_config(context: 'Context', game: str) -> 'Union[GameConfig,None]':
    """Utility function to check if the current guild has a certain game configured

    :param context: The Discord Context.
    :param game: The game to check for.
    :return: Game Configuration or None"""
    game_config = await sync_to_async(GameConfig.get_by_game_alias)(
        game,
        context.guild.id
    )
    if game_config is None:
        await context.send(
            f'Game {game} either does not exist or is not available in this Guild.'
        )
        return None
    return game_config


async def get_game_categories(
    context: 'Context', game_config: 'GameConfig'
) -> 'Union[List[DiscordCategory],None]':
    """Utility function to get the category configured for a certain game

    :param context: The Discord Context.
    :param game_config: The GameConfig to use to query
    :return: Categories in the server for the game or None"""
    return list(
        filter(lambda x: x.name == game_config.game.name, context.guild.categories)
    )


async def create_channel_in_db(
    context: 'Context',
    game_config: 'GameConfig',
    channel_id: str
) -> Channel:
    """Utility function to create a channel in the database

    :param context: The Discord Context.
    :param game_config: The GameConfig to use for extra info.
    :return: The Channel that was created"""
    owner = (await sync_to_async(User.objects.get_or_create)(id=context.author.id))[0]
    return await sync_to_async(Channel.objects.create)(
        id=channel_id,
        owner=owner, guild_id=context.guild.id, game=game_config.game
    )


def get_game_completion_role(
    context: 'Context',
    game_config: 'GameConfig'
) -> 'Union[Role,None]':
    """Utility function to get the completion role in the guild

    :param context: The Discord Context.
    :param game_config: The game to get the completion role for.
    :return: The Role or None"""
    return get(context.guild.roles, id=int(game_config.completion_role_id))


async def grant_completion_role(context: 'Context', game_config: 'GameConfig'):
    """Grant the message author the completion role for a certain game.

    :param context: The Discord Context.
    :param game_config: The game to get the completion role for."""
    completion_role = get_game_completion_role(context, game_config)
    await context.message.author.add_roles(completion_role)


async def archive_channel(context: 'Context', channel: 'Channel'):
    """Utility to archive a playthrough channel for a certain game

    :param context: The Discord Context
    :param channel: The Channel to archive."""
    channel_in_guild = get(context.guild.channels, id=int(channel.id))
    if not channel_in_guild:
        return
    exported_channel_file_path = export_channel(channel.id)
    exported_channel_file = File(
        file=open(exported_channel_file_path),
        name=exported_channel_file_path.name
    )
    await channel_in_guild.delete()
    await sync_to_async(Archive.objects.create)(
        channel=channel,
        file=exported_channel_file
    )
    exported_channel_file.close()
    exported_channel_file_path.unlink()


async def get_permissions(
    context: 'Context', game_config: 'GameConfig'
) -> 'Union[dict,None]':
    """Get permissions for a playthrough channel

    :param context: The Discord Context
    :param game_config: The game to get the permissions for."""
    completion_role = get_game_completion_role(context, game_config)
    if completion_role is None:
        await context.send((
            f'There seems to be a misconfiguration for {game_config.game}'
            ' on the server. Please contact an admin.'
        ))
        return None
    permissions = {
        context.message.guild.me: PermissionOverwrite(
            read_messages=True,
            read_message_history=True,
            manage_messages=True,
            send_messages=True,
        ),
        context.message.guild.default_role: PermissionOverwrite(
            read_messages=False,
            read_message_history=False,
        ),
        context.message.author: PermissionOverwrite(
            read_messages=True,
            read_message_history=True,
            send_messages=True,
            manage_messages=True,
            manage_channels=True,
        ),
        completion_role: PermissionOverwrite(
            read_messages=True,
            read_message_history=True,
        )
    }
    return permissions


async def create_channel(
    context: 'Context',
    game_config: 'GameConfig',
    name: str,
    permissions: dict
) -> 'Union[DiscordChannel,None]':
    """Creates a new playthrough channel in the guild.

    :param context: The Discord Context
    :param game_config: The game to create a channel for.
    :param name: The channel name.
    :param permissions: The permission overwrites for the channel.
    :param logger: The Logger to use to log things.
    """
    # Get category & channel name
    categories = await get_game_categories(context, game_config)
    channel_created = False
    for category in categories:
        try:
            channel = await context.guild.create_text_channel(
                name=name, category=category, overwrites=permissions
            )
            channel_created = True
        except HTTPException:
            pass
    if not channel_created:
        try:
            logger.warn((
                f'Cap on categories for game `{game_config.game}` reached.'
                ' Creating a new one...'
            ))
            position = None
            if len(categories) > 0:
                position = categories[-1].position + 1
            category = await context.guild.create_category(
                name=game_config.game.name, position=position
            )
            logger.info(f"Created new category for {game_config.game}.")
            channel = await context.guild.create_text_channel(
                name=name, category=category, overwrites=permissions
            )
            logger.info(f"Created channel {name}.")
        except (HTTPException) as e:
            logger.error(
                f'Error occurred when creating channel {name}', e
            )
            return None
    return channel


class Playthrough(Cog):
    logger = logging.getLogger(__name__)

    instructions = (
        "Test Instructions"
    )

    def __init__(self, client):
        self.client = client
        self.logger.info(f'Module {self.__class__.__name__} loaded successfully.')

    @command(pass_context=True)
    async def play(self, context, *, game: str):
        """Create a playthrough channel and start playing."""
        # Get game config
        game_config = await get_game_config(context, game)
        if not game_config:
            await context.send((
                f'Game {game} does not exist, or it is not configured in this guild.'
            ))
            return
        # Check for existing channel
        existing_channel = await get_existing_channel(context, game_config.game)
        if existing_channel:
            await context.send((
                f'You already have a channel for `{game_config.game}`! '
                'You can only have one at a time. Even if you have one archived. '
                f'If you want to continue playing, use `{PREFIX}resume`! '
                'If this is an error ask a moderator for help. '
            ))
            return
        # Channel name
        channel_name = (
            f'{context.author.display_name.lower()}'
            f'{game_config.game.channel_suffix.lower()}'
        )
        # Set Permissions
        permissions = await get_permissions(context, game_config)
        if permissions is None:
            return
        # Try creating the channel
        channel = await create_channel(context, game_config, channel_name, permissions)
        if channel is None:
            return
        # Create channel in the database
        await create_channel_in_db(context, game_config, channel.id)
        # Send instructions & pin
        instructions_msg = await channel.send(self.instructions)
        await channel.send(context.message.author.mention)
        await instructions_msg.pin()
        await context.send(f'Successfully created your channel: {channel_name}')

    @command(pass_context=True)
    async def replay(self, context, *, game: str):
        """Create a replay channel."""
        pass

    @command(pass_context=True)
    async def drop(self, context, *, game: str):
        """Drop a game. Closes playthrough channel."""
        await context.trigger_typing()
        # Get game config
        game_config = await get_game_config(context, game)
        if not game_config:
            await context.send((
                f'Game {game} does not exist, or it is not configured in this guild.'
            ))
            return
        existing_channel = await get_existing_channel(context, game_config.game)
        if existing_channel:
            await archive_channel(context, existing_channel)
            await context.send(f'And that\'s that. You dropped {game_config.game}.')
        else:
            await context.send((
                'You don\'t seem to be playing the game (have a channel). '
                'So this command does nothing.'
            ))

    @command(pass_context=True)
    async def resume(self, context, *, game: str):
        """Resume playing a game. Re-creates playthrough channel."""
        pass

    @command(pass_context=True)
    async def finish(self, context, *, game: str):
        """Finish playing a game. Archives playthrough channel."""
        await context.trigger_typing()
        # Get game config
        game_config = await get_game_config(context, game)
        if not game_config:
            await context.send((
                f'Game {game} does not exist, or it is not configured in this guild.'
            ))
            return
        existing_channel = await get_existing_channel(context, game_config.game)
        if existing_channel:
            await archive_channel(context, existing_channel)
            existing_channel.finished = True
            await sync_to_async(existing_channel.save)()
        await grant_completion_role(context, game_config)
        await context.send((
            f'Hope you enjoyed {game_config.game}! '
            'If you had a channel it should be archived and you should now'
            ' be able to see global spoiler channels!'
        ))

    @command(pass_context=True)
    async def reset(self, context, *, game: str):
        """Reset history on a certain game. Removes completion role."""
        pass


def setup(client):
    client.add_cog(Playthrough(client))
