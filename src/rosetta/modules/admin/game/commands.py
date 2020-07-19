from typing import TYPE_CHECKING

from asgiref.sync import sync_to_async
import click

from playthrough.models import Game, Alias, Series, RoleTemplate
from rosetta.utils import ask
from .utils import games_list_to_embed, game_to_embed

if TYPE_CHECKING:
    from typing import Union, Tuple
    from click import Context


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
@click.option('--series', '-s', type=str, help='name or alias of the series')
@click.pass_context
async def add(context: 'Context', name: str, series: str):
    """Command to add a game"""
    discord_context = context.obj["discord_context"]
    try:
        series = await sync_to_async(Series.get_by_name_or_alias)(series)
    except (Series.DoesNotExist):
        series = None
    async with discord_context.typing():
        game, created = await _create_game(name, series)
        if created:
            await discord_context.send(f'Game `{game}` was successfully created!')
        else:
            await discord_context.send(f'Game `{game}` seems to already exist.')


@click.command()
@click.argument('game', type=str)
@click.option('--yes', '-y', is_flag=True, help='confirm the deletion')
@click.pass_context
async def remove(context: 'Context', game: str, yes: bool = False):
    """Command to remove a game"""
    discord_context = context.obj["discord_context"]
    game_obj = await _get_game(game)
    if game_obj is None:
        await discord_context.send(
            f'Sorry, it seems that game `{game}` wasn\'t found in our database.'
        )
        return
    if not yes:
        message = await ask(
            discord_context,
            f'Are you sure you want to delete the game `{game_obj}`? (Y/N)',
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
        await sync_to_async(game_obj.delete)()
        await discord_context.send(f'Poof! Game `{game_obj}` is gone!')


@click.command()
@click.argument('game', type=str)
@click.option('--name', '-n', type=str, help='new name of the game')
@click.option('--series', '-s', type=str, help='name or alias of the series')
@click.option(
    '--channel-suffix', '-cf', type=str, help='the suffix for the game\'s channels'
)
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
    series: str = None,
    channel_suffix: str = None,
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
        if series is not None:
            try:
                await discord_context.send(f'Setting series to: `{series}`...')
                series_obj = await sync_to_async(Series.get_by_name_or_alias)(series)
                game_obj.series = series_obj
                await sync_to_async(game_obj.save)()
            except (Series.DoesNotExist):
                await discord_context.send('Failed to set series.')
                await discord_context.send(
                    f'Series `{series}` was not found in our database.'
                )
        if channel_suffix is not None:
            await discord_context.send(
                f'Setting channel suffix to: `{channel_suffix}`...'
            )
            game_obj.channel_suffix = channel_suffix
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


@click.command()
@click.argument('game', type=str)
@click.option('--name', '-n', type=str, help='the name of the role')
@click.option('--colour', '-c', type=str, help='hex code for the colour of the role.')
@click.pass_context
async def set_role_template(
    context: 'Context', game: str, name: str = None, colour: str = None
):
    """Command to set the game's completion role template"""
    discord_context = context.obj["discord_context"]
    game_obj = await _get_game(game)
    if game_obj is None:
        await discord_context.send(
            f'Sorry, it seems that game `{game}` wasn\'t found in our database.'
        )
        return
    if name is not None or colour is not None:
        if game_obj.completion_role is not None:  # Update
            if name is not None:
                await discord_context.send(f'Setting name to {name}...')
                game_obj.completion_role.name = name
            if colour is not None:
                game_obj.completion_role.colour = colour.replace('#', '')
                if not game_obj.completion_role.is_valid():
                    await discord_context.send(f'Invalid colour: {colour}. Is it hex?')
                    return
                await discord_context.send(f'Setting name to {colour}...')
            await sync_to_async(game_obj.completion_role.save)()
            await discord_context.send(
                f'Saved changes to {game_obj}\'s Completion Role Template!'
            )
        else:  # Create
            if name is None:
                await discord_context.send('Role template name is required!')
                return
            template = RoleTemplate(name=name, colour=colour.replace('#', ''))
            if not template.is_valid():
                await discord_context.send(f'Invalid colour: {colour}. Is it hex?')
                return
            await sync_to_async(template.save)()
            game_obj.completion_role = template
            await sync_to_async(game_obj.save)()
            await discord_context.send(f'Created role template `{template}`!')
    else:
        await discord_context.send(
            'Please provide at least 1 option. Either `--name` or `--colour`!'
        )


@click.command()
@click.argument('game', type=str)
@click.option('--yes', '-y', is_flag=True, help='confirm the deletion')
@click.pass_context
async def remove_role_template(context: 'Context', game: str, yes: bool = False):
    """Command to set the game's completion role template"""
    discord_context = context.obj["discord_context"]
    game_obj = await _get_game(game)
    if game_obj is None:
        await discord_context.send(
            f'Sorry, it seems that game `{game}` wasn\'t found in our database.'
        )
        return
    if game_obj.completion_role is not None:  # Update
        if not yes:
            message = await ask(
                discord_context,
                (f'Are you sure you want to delete the game\'s `{game_obj}`',
                 'role template? (Y/N)'),
                lambda m: m.content.lower() in ['y', 'n', 'yes', 'no']
            )
            if message is None:
                await discord_context.send(
                    'You forgot to reply! Will take that as a no.'
                )
            else:
                if message.content.lower() in ['y', 'yes']:
                    yes = True
                else:
                    await discord_context.send('Alright then!')
        if yes:
            await sync_to_async(game_obj.completion_role.delete)()
            await discord_context.send(
                f'Poof! The role template for game `{game_obj}` is gone!'
            )
    else:  # Create
        await discord_context.send(
            f'The game {game_obj} doesn\'t have a role template... Are you okay?'
        )


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
    'set_role_template',
    'remove_role_template',
    '_list',
]
