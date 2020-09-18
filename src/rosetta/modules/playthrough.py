import logging
from typing import TYPE_CHECKING

from asgiref.sync import sync_to_async
from discord import HTTPException, PermissionOverwrite
from discord.ext.commands import Cog, command
from discord.utils import get
from playthrough.models import Channel, Game, GameConfig, User

if TYPE_CHECKING:
    from typing import Union, List
    from discord import CategoryChannel as DiscordCategory
    from discord import TextChannel as DiscordChannel
    from discord import Role
    from discord.ext.commands import Context


async def get_existing_channel(
    context: 'Context', game: 'Game'
) -> 'Union[DiscordChannel,None]':
    """Utility function to get the existing channel for a user for a game.

    :param context: The Discord Context.
    :param game: The game to get the channel for.
    :return: Existing Channel in the guild for a certain game or None"""
    existing_channel = await sync_to_async(Channel.objects.filter(
        owner_id=context.author.id, game=game
    ).first)()
    if existing_channel is not None:
        # If the user supposedly has an existing channel
        # if it's not in the guild, remove from the DB
        channel_in_guild = get(context.guild.channels, id=int(existing_channel.id))
        if channel_in_guild is None:
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


def get_channel_completion_role(
    context: 'Context',
    game_config: 'GameConfig'
) -> 'Union[Role,None]':
    """Utility function to get the completion role in the guild

    :param context: The Discord Context.
    :param game_config: The game to get the completion role for.
    :return: The Role or None"""
    return get(context.guild.roles, id=int(game_config.completion_role_id))


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
        game_obj = game_config.game
        # Check for existing channel
        owner = context.message.author
        existing_channel = await get_existing_channel(context, game_config.game)
        if existing_channel:
            await context.send((
                f'You already have a channel for `{game_config.game}`! '
                'You can only have one at a time. If this is an error ask a moderator'
                'for help.'
            ))
            return
        # Get category & channel name
        categories = await get_game_categories(context, game_config)
        channel_name = (
            f'{context.author.display_name.lower()}'
            f'{game_config.game.channel_suffix.lower()}'
        )
        # Set Permissions
        completion_role = get_channel_completion_role(context, game_config)
        if completion_role is None:
            await context.send((
                f'There seems to be a misconfiguration for {game_config.game}'
                ' on the server. Please contact an admin.'
            ))
            return
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
            owner: PermissionOverwrite(
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
        # Try creating the channel
        channel_created = False
        for category in categories:
            try:
                channel = await context.guild.create_text_channel(
                    name=channel_name, category=category, overwrites=permissions
                )
                channel_created = True
            except HTTPException:
                pass
        if not channel_created:
            try:
                self.logger.warn((
                    f'Cap on categories for game `{game_config.game}` reached.'
                    ' Creating a new one...'
                ))
                position = None
                if len(categories) > 0:
                    position = categories[-1].position + 1
                category = await context.guild.create_category(
                    name=game_obj.name, position=position
                )
                self.logger.info(f"Created new category for {game_config.game}.")
                channel = await context.guild.create_text_channel(
                    name=channel_name, category=category, overwrites=permissions
                )
                self.logger.info(f"Created channel {channel_name}.")
            except (HTTPException) as e:
                self.logger.error(
                    f'Error occurred when creating channel {channel_name}', e
                )
                return
        # Create channel in the database
        await create_channel_in_db(context, game_config, channel)
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
        pass

    @command(pass_context=True)
    async def resume(self, context, *, game: str):
        """Resume playing a game. Re-creates playthrough channel."""
        pass

    @command(pass_context=True)
    async def finish(self, context, *, game: str):
        """Finish playing a game. Archives playthrough channel."""
        pass

    @command(pass_context=True)
    async def reset(self, context, *, game: str):
        """Reset history on a certain game. Removes completion role."""
        pass


def setup(client):
    client.add_cog(Playthrough(client))
