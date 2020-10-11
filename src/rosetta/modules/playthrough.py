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
    ).prefetch_related('archives').first)()
    if existing_channel is not None:
        # If the user supposedly has an existing channel
        # if it's not in the guild, remove from the DB
        channel_in_guild = get(context.guild.channels, id=int(existing_channel.id))
        if channel_in_guild is None and len(existing_channel.archives.all()) == 0:
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
    channel_id: str,
    finished: bool = False
) -> Channel:
    """Utility function to create a channel in the database

    :param context: The Discord Context.
    :param game_config: The GameConfig to use for extra info.
    :param finished: Whether or not the channel is finished.
    :return: The Channel that was created"""
    owner = (await sync_to_async(User.objects.get_or_create)(id=context.author.id))[0]
    return await sync_to_async(Channel.objects.create)(
        id=channel_id,
        owner=owner, guild_id=context.guild.id, game=game_config.game,
        finished=finished
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


async def remove_completion_role(context: 'Context', game_config: 'GameConfig'):
    """Removes the completion role for a certain game from the message author.

    :param context: The Discord Context.
    :param game_config: The game to get the completion role for."""
    completion_role = get_game_completion_role(context, game_config)
    await context.message.author.remove_roles(completion_role)


async def archive_channel(context: 'Context', channel: 'Channel'):
    """Utility to archive a playthrough channel for a certain game

    :param context: The Discord Context
    :param channel: The Channel to archive."""
    channel_in_guild = get(context.guild.channels, id=int(channel.id))
    if not channel_in_guild:
        return
    await context.send('Archiving channel, this might take a while....')
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
    for category in categories:
        try:
            channel = await context.guild.create_text_channel(
                name=name, category=category, overwrites=permissions
            )
            return channel
        except HTTPException:
            pass

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
        return channel
    except (HTTPException) as e:
        logger.error(
            f'Error occurred when creating channel {name}', e
        )
        return None


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
            if len(existing_channel.archives.all()) > 0:
                have = "had"
            else:
                have = "have"
            message = (
                f'You already {have} a channel for `{game_config.game}`! '
            )
            if existing_channel.finished:
                message += f'If you want to replay, use `{PREFIX}replay {game}`! '
            else:
                message += (
                    'If you want to continue playing, '
                    f'use `{PREFIX}resume {game}`. '
                )
            message += 'If this is an error ask a moderator for help. '
            await context.send(message)
            return
        # Check if the user already finished the game
        completion_role = get_game_completion_role(context, game_config)
        if completion_role in context.message.author.roles:
            await context.send((
                f'Looks like you have already played {game_config.game}. '
                f'Try `{PREFIX}replay {game}`.'
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
        await context.send(f'Successfully created your channel: {channel.mention}')

    @command(pass_context=True)
    async def replay(self, context, *, game: str):
        """Create a replay channel."""
        # Get game config
        game_config = await get_game_config(context, game)
        if not game_config:
            await context.send((
                f'Game {game} does not exist, or it is not configured in this guild.'
            ))
            return
        # Check for existing channel / completion status
        completion_role = get_game_completion_role(context, game_config)
        existing_channel = await get_existing_channel(context, game_config.game)
        author = context.message.author
        if existing_channel is not None:
            channel_in_guild = get(context.guild.channels, id=int(existing_channel.id))
        else:
            channel_in_guild = None
        if existing_channel is None and completion_role not in author.roles:
            await context.send((
                f'Doesn\'t seem like you have played {game_config.game} yet. '
                f'Try `{PREFIX}play {game}`.'
            ))
            return
        elif existing_channel is not None and not existing_channel.finished:
            await context.send((
                f'Doesn\'t seem like you have finished {game_config.game} yet.'
            ))
            return
        elif channel_in_guild is not None:
            await context.send((
                f'Seems like you still have a replay channel for {game_config.game} '
                'in this server.'
            ))
            return
        # Channel name
        channel_name = (
            f'{context.author.display_name.lower()}'
            f'{game_config.game.channel_suffix.lower()}'.replace('play', 'replay')
        )
        # Set Permissions
        permissions = await get_permissions(context, game_config)
        if permissions is None:
            return
        # Try creating the channel
        channel = await create_channel(context, game_config, channel_name, permissions)
        if channel is None:
            return
        # Update channel in the database
        if not existing_channel:
            existing_channel = await create_channel_in_db(
                context, game_config, channel.id, finished=True
            )
        else:
            await sync_to_async(existing_channel.update_id)(channel.id)
        # Send instructions & pin
        instructions_msg = await channel.send(self.instructions)
        await channel.send(author.mention)
        await instructions_msg.pin()
        await context.send(
            f'Successfully created your replay channel: {channel.mention}'
        )

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
        # Get game config
        game_config = await get_game_config(context, game)
        if not game_config:
            await context.send((
                f'Game {game} does not exist, or it is not configured in this guild.'
            ))
            return
        # Check for existing channel / completion status
        existing_channel = await get_existing_channel(context, game_config.game)
        author = context.message.author
        channel_in_guild = get(context.guild.channels, id=int(existing_channel.id))
        if existing_channel is None:
            await context.send((
                f'Doesn\'t seem like you have played {game_config.game} yet. '
                f'Try `{PREFIX}play {game}`.'
            ))
            return
        elif existing_channel is not None and existing_channel.finished:
            await context.send((
                f'Seems like you have already finished {game_config.game}. '
                f'Try `{PREFIX}replay {game}`.'
            ))
            return
        elif channel_in_guild is not None:
            await context.send((
                'Seems like you still have a playthrough channel '
                f'for {game_config.game} in this server.'
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
        # Update channel in the database
        await sync_to_async(existing_channel.update_id)(channel.id)
        # Send instructions & pin
        instructions_msg = await channel.send(self.instructions)
        await channel.send(author.mention)
        await instructions_msg.pin()
        await context.send(
            f'Successfully created your resume channel: {channel.mention}'
        )

    @command(pass_context=True)
    async def finish(self, context, *, game: str):
        """Finish playing a game.
        Grants completion role & archives any playthrough channel."""
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
        await context.trigger_typing()
        # Get game config
        game_config = await get_game_config(context, game)
        if not game_config:
            await context.send((
                f'Game {game} does not exist, or it is not configured in this guild.'
            ))
            return
        await remove_completion_role(context, game_config)
        await context.send((
            f'Your progress on {game_config.game} has been reset. '
            'The completion role is removed!'
        ))
        pass


def setup(client):
    client.add_cog(Playthrough(client))
