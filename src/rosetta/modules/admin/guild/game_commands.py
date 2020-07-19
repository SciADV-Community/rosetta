from typing import TYPE_CHECKING

from asgiref.sync import sync_to_async
import click
from discord import Colour
from discord.utils import get

from playthrough.models import GameConfig, Game, Category
from rosetta.utils import ask
from .utils import game_config_to_embed, config_list_to_embed

if TYPE_CHECKING:
    from typing import Union, List
    from click import Context


@sync_to_async
def _get_game(game: str) -> 'Union[Game,None]':
    try:
        return Game.get_by_name_or_alias(game)
    except (Game.DoesNotExist):
        return None


@sync_to_async
def _get_game_config(guild_id: str, game: str) -> 'Union[GameConfig,None]':
    try:
        game = Game.get_by_name_or_alias(game)
        try:
            return GameConfig.objects\
                .select_related('category', 'game', 'guild').get(
                    guild_id=guild_id, game=game
                )
        except (GameConfig.DoesNotExist):
            return None
    except (Game.DoesNotExist):
        return None


@sync_to_async
def _get_all_game_configs(guild_id: str) -> 'List[GameConfig]':
    return list(
        GameConfig.objects.select_related('game', 'guild', 'category')
        .filter(guild_id=guild_id).all()
    )


@sync_to_async
def _get_category(_id: str, guild_id: str) -> Category:
    return Category.objects.get_or_create(id=_id, guild_id=guild_id)[0]


@click.group()
@click.pass_context
def game(context: 'Context'):
    """Manage game operations"""
    pass


@game.command()
@click.argument('game', type=str)
@click.option('--create-role', '-cr', is_flag=True, help='create the completion role')
@click.option(
    '--role-id', '-r', type=str, help='the id of the completion role'
)
@click.option(
    '--category-id', '-c', type=str, help='the id the category to add new channels to'
)
@click.pass_context
async def add(
    context: 'Context',
    game: str,
    create_role: bool = False,
    role_id: str = None,
    category_id: str = None
):
    """Command to add a game to the guild."""
    discord_context = context.obj["discord_context"]
    game_config = await _get_game_config(discord_context.guild.id, game)
    if game_config is not None:
        await discord_context.send(
            (f'Game game `{game_config.game}` is already added to the Guild.\n'
             'Use `update-game` to update its configuration.')
        )
        return
    game_obj = await _get_game(game)
    if game_obj is None:
        await discord_context.send(
            f'Sorry, it seems that game `{game}` wasn\'t found in our database.'
        )
        return
    category_obj = None
    if category_id is not None:
        category = get(discord_context.guild.categories, id=int(category_id))
        if category is None:
            await discord_context.send(
                f'Category `{category_id}` not found in the Guild.'
            )
        else:
            category_obj = await _get_category(category_id, discord_context.guild.id)
    if role_id is not None:
        role = get(discord_context.guild.roles, id=int(role_id))
        if role is None:
            await discord_context.send(f'Role `{role_id}` not found in the Guild.')
            role_id = None
    if role_id is None and not create_role:
        message = await ask(
            discord_context,
            ('Invalid or no role provided. '
             'Would you like to create it from the game\'s template? (Y/N)'),
            lambda m: m.content.lower() in ['y', 'n', 'yes', 'no']
        )
        if message is None:
            await discord_context.send('You forgot to reply! Will take that as a no.')
            return
        else:
            if message.content.lower() in ['y', 'yes']:
                create_role = True
            else:
                await discord_context.send('Alright then!')
                return
    if create_role:
        role = game_obj.completion_role
        if role is None:
            await discord_context.send((
                f'The game `{game_obj}` has no role template. '
                'Please either register one or provide a role id.'
            ))
            return
        colour = None
        if role.colour is not None:
            colour = Colour.from_rgb(*role.get_colour_as_rgb())
        discord_role = await discord_context.guild.create_role(
            name=role.name, colour=colour
        )
        role_id = discord_role.id
    await sync_to_async(GameConfig.objects.create)(
        game=game_obj,
        guild_id=discord_context.guild.id,
        category=category_obj,
        completion_role_id=role_id
    )
    await discord_context.send(f'Added `{game_obj}` to the guild!')


@game.command()
@click.argument('game', type=str)
@click.option('--yes', '-y', is_flag=True, help='confirm the removal')
@click.pass_context
async def remove(context: 'Context', game: str, yes: bool = False):
    """Command to remove a game from the guild."""
    discord_context = context.obj["discord_context"]
    game_config = await _get_game_config(discord_context.guild.id, game)
    if game_config is None:
        await discord_context.send(
            (f'Configuration for `{game}` not found. '
             'Does the game exist and is it added to the Guild?')
        )
        return
    if not yes:
        message = await ask(
            discord_context,
            f'Are you sure you want to remove game `{game_config.game}`? (Y/N)',
            lambda m: m.content.lower() in ['y', 'n', 'yes', 'no']
        )
        if message is None:
            await discord_context.send('You forgot to reply! Will take that as a no.')
        else:
            if message.content.lower() in ['y', 'yes']:
                yes = True
            else:
                await discord_context.send('Alright then!')
    if yes:
        await sync_to_async(game_config.delete)()
        await discord_context.send(
            f'Poof! Game `{game_config.game}` is no longer configured!'
        )


@game.command()
@click.argument('game', type=str)
@click.option('--role-id', '-r', type=str, help='the id of the completion role')
@click.option(
    '--category-id', '-c', type=str, help='the id the category to add new channels to'
)
@click.pass_context
async def update(
    context: 'Context',
    game: str,
    role_id: str = None,
    category_id: str = None
):
    """Command to update a game's configuration for the guild."""
    discord_context = context.obj["discord_context"]
    game_config = await _get_game_config(discord_context.guild.id, game)
    if game_config is None:
        await discord_context.send(
            (f'Configuration for `{game}` not found.',
             'Does the game exist and is it added to the Guild?')
        )
        return
    if role_id is None and category_id is None:
        await discord_context.send(
            'Expecting at least 1 option. Use `--help` if you need help.'
        )
        return
    if role_id is not None:
        await discord_context.send(f'Setting completion role id to: `{role_id}`...')
        game_config.completion_role_id = role_id
        if not game_config.is_valid():
            await discord_context.send(f'Invalid role id {role_id}.')
        else:
            role = get(discord_context.guild.roles, id=int(role_id))
            if role is None:
                await discord_context.send(f'Role `{role_id}` not found in the Guild.')
            else:
                await sync_to_async(game_config.save)()
    if category_id is not None:
        category = get(discord_context.guild.categories, id=int(category_id))
        if category is None:
            await discord_context.send(
                f'Category `{category_id}` not found in the Guild.'
            )
        else:
            await discord_context.send(f'Setting category to: `{category.name}`...')
            game_config.category = await _get_category(
                category_id, discord_context.guild.id
            )
            await sync_to_async(game_config.save)()
    await discord_context.send(f'Successfully saved changes to {game_config}!')


@game.command(name='list')
@click.argument('game', type=str, required=False)
@click.pass_context
async def _list(context: 'Context', game: str = None):
    """Command to list configured games or inspect a specific one."""
    discord_context = context.obj['discord_context']
    if game is not None:
        game_config = await _get_game_config(
            discord_context.guild.id, game
        )
        if game_config is None:
            await discord_context.send((
                'Either game does not exist'
                'or it has not been configured for this Guild.'
            ))
            return
        embed = game_config_to_embed(game_config, discord_context)
        await discord_context.send(embed=embed)
    else:
        all_guild_games = await _get_all_game_configs(discord_context.guild.id)
        embed = config_list_to_embed(all_guild_games)
        await discord_context.send(embed=embed)


__all__ = [
    'game'
]
