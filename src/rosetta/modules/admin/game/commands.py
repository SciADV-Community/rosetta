from typing import TYPE_CHECKING

from asgiref.sync import sync_to_async
import click

from playthrough.models import Game, Alias, Series
from .utils import games_list_to_embed, game_to_embed

if TYPE_CHECKING:
    from typing import Union, Tuple
    from click import Context
    from discord import Message


@sync_to_async
def _get_game(game_name: str) -> 'Union[Game,None]':
    try:
        return Game.get_by_name_or_alias(name=game_name)
    except Game.DoesNotExist:
        return None


@sync_to_async
def _get_all_games():
    return list(Game.objects.all())


@sync_to_async
def _create_game(name: str, series: Series) -> 'Tuple[Game,bool]':
    return Game.objects.get_or_create(name=name, series=series)


@sync_to_async
def _delete_alias(alias: str):
    Alias.objects.filter(alias=alias).delete()


@click.command()
@click.option('--name', '-n', type=str, help='name of the series', required=True)
@click.option(
    '--series', '-s', type=str, help='name or alias of the series', required=True
)
@click.pass_context
async def add(context: 'Context', name: str, series: str):
    """Command to add a game"""
    discord_context = context.obj["discord_context"]
    try:
        series = await sync_to_async(Series.get_by_name_or_alias)(series)
        async with discord_context.typing():
            game, created = await _create_game(name, series)
            if created:
                await discord_context.send(f'Game `{game}` was successfully created!')
            else:
                await discord_context.send(f'Game `{game}` seems to already exist.')
    except (Series.DoesNotExist):
        await discord_context.send(f'Series `{series}` was not found in our database.')


@click.command()
@click.argument('game', type=str)
@click.pass_context
async def remove(context: 'Context', game: str):
    """Command to remove a game"""
    discord_context = context.obj["discord_context"]
    channel = discord_context.channel
    game_obj = await _get_game(game)
    if game_obj is None:
        await discord_context.send(
            f'Sorry, it seems that game `{game}` wasn\'t found in our database.'
        )
        return

    await discord_context.send(
        f'Are you sure you want to delete the game `{game}`? (Y/N)'
    )

    def check(m: 'Message') -> bool:
        return m.channel == channel and m.content.lower() in ['y', 'n', 'yes', 'no']

    message = await discord_context.bot.wait_for('message', check=check, timeout=15)
    if message is None:
        await discord_context.send('You forgot to reply! Will take that as a no.')
    else:
        if message.content.lower() in ['y', 'yes']:
            await sync_to_async(game_obj.delete)()
            await discord_context.send(f'Poof! Game `{game}` is gone!')
        else:
            await discord_context.send('Alright then!')


@click.command()
@click.argument('game', type=str)
@click.option('--name', '-n', type=str, help='new name of the game')
@click.option(
    '--add-aliases', '-na', type=str, help='comma separated list of aliases to add'
)
@click.option(
    '--remove-aliases', '-da', type=str,
    help='comma separated list of aliases to remove'
)
@click.pass_context
async def update(
    context: 'Context',
    game: str,
    name: str = None,
    add_aliases: str = None,
    remove_aliases: str = None
):
    """Command to update a game"""
    discord_context = context.obj["discord_context"]
    game_obj = await _get_game(game)
    if game_obj is None:
        await discord_context.send(
            f'Sorry, it seems that game `{game}` wasn\'t found in our database.'
        )
    else:
        if name is not None:
            await discord_context.send(f'Setting name to: `{name}`...')
            game_obj.name = name
            await sync_to_async(game_obj.save)()
        if add_aliases is not None:
            aliases = set([alias.lower() for alias in add_aliases.split(',')])
            for alias in [a for a in aliases if len(a) > 2]:
                await discord_context.send(f'Adding alias: `{alias}`...')
                await sync_to_async(Alias.objects.create)(
                    content_object=game_obj, alias=alias
                )
        if remove_aliases is not None:
            aliases = set([alias.lower() for alias in remove_aliases.split(',')])
            for alias in [a for a in aliases if len(a) > 2]:
                await discord_context.send(f'Removing alias: `{alias}`...')
                await _delete_alias(alias)
        await discord_context.send('Successfully saved changes!')


@click.command(name='list')
@click.argument('game', type=str, required=False)
@click.pass_context
async def _list(context: 'Context', game: str = None):
    """Command to list all or a specific game"""
    discord_context = context.obj["discord_context"]
    if game is None:
        all_games = await _get_all_games()
        if len(all_games) == 0:
            await discord_context.send('No games currently registered!')
            return

        await discord_context.send(embed=games_list_to_embed(all_games))
    else:
        game_obj = await _get_game(game)
        if game_obj is None:
            await discord_context.send(
                f'Sorry, it seems that game `{game}` wasn\'t found in our database.'
            )
        else:
            embed = await sync_to_async(game_to_embed)(game_obj)
            await discord_context.send(embed=embed)


__all__ = [
    'add',
    'remove',
    'update',
    '_list',
]
