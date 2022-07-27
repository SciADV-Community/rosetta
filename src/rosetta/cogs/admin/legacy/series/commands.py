from typing import TYPE_CHECKING

from asgiref.sync import sync_to_async
import click

from playthrough.models import Series, Alias
from rosetta.utils import ask
from .utils import series_list_to_embed, series_to_embed

if TYPE_CHECKING:
    from typing import Union, Tuple
    from click import Context


@sync_to_async
def _get_series(series_name: str) -> 'Union[Series,None]':
    try:
        return Series.get_by_name_or_alias(name=series_name)
    except Series.DoesNotExist:
        return None


@sync_to_async
def _get_all_series():
    return list(Series.objects.all())


@sync_to_async
def _create_series(name: str) -> 'Tuple[Series,bool]':
    return Series.objects.get_or_create(name=name)


@sync_to_async
def _delete_alias(alias: str):
    Alias.objects.filter(alias=alias).delete()


@click.command()
@click.option('--name', '-n', type=str, help='name of the series', required=True)
@click.pass_context
async def add(context: 'Context', name: str):
    """Command to add a series"""
    discord_context = context.obj["discord_context"]
    async with discord_context.typing():
        series, created = await _create_series(name)
        if created:
            await discord_context.send(f'Series `{series}` was successfully created!')
        else:
            await discord_context.send(f'Series `{series}` seems to already exist.')


@click.command()
@click.argument('series', type=str)
@click.option('--yes', '-y', is_flag=True, help='confirm the deletion')
@click.pass_context
async def remove(context: 'Context', series: str, yes: bool = False):
    """Command to remove a series"""
    discord_context = context.obj["discord_context"]
    series_obj = await _get_series(series)
    if series_obj is None:
        await discord_context.send(
            f'Sorry, it seems that series `{series}` wasn\'t found in our database.'
        )
        return
    if not yes:
        message = await ask(
            discord_context,
            f'Are you sure you want to delete series `{series_obj}`? (Y/N)',
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
        await sync_to_async(series_obj.delete)()
        await discord_context.send(f'Poof! Series `{series_obj}` is gone!')


@click.command()
@click.argument('series', type=str)
@click.option('--name', '-n', type=str, help='new name of the series')
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
    series: str,
    name: str = None,
    add_aliases: str = None,
    remove_aliases: str = None
):
    """Command to update a series"""
    discord_context = context.obj["discord_context"]
    series_obj = await _get_series(series)
    if series_obj is None:
        await discord_context.send(
            f'Sorry, it seems that series `{series}` wasn\'t found in our database.'
        )
        return
    if name is None and add_aliases is None and remove_aliases is None:
        await discord_context.send(
            'Expecting at least 1 option. Use `--help` if you need help.'
        )
        return
    if name is not None:
        await discord_context.send(f'Setting name to: `{name}`...')
        series_obj.name = name
        await sync_to_async(series_obj.save)()
    if add_aliases is not None:
        aliases = set([alias.lower() for alias in add_aliases.split(',')])
        for alias in [a for a in aliases if len(a) > 2]:
            await discord_context.send(f'Adding alias: `{alias}`...')
            await sync_to_async(Alias.objects.create)(
                content_object=series_obj, alias=alias
            )
    if remove_aliases is not None:
        aliases = set([alias.lower() for alias in remove_aliases.split(',')])
        for alias in [a for a in aliases if len(a) > 2]:
            await discord_context.send(f'Removing alias: `{alias}`...')
            await _delete_alias(alias)
    await discord_context.send(f'Successfully saved changes to `{series_obj}`!')


@click.command(name='list')
@click.argument('series', type=str, required=False)
@click.pass_context
async def _list(context: 'Context', series: str = None):
    """Command to list all or a specific series"""
    discord_context = context.obj["discord_context"]
    if series is None:
        all_series = await _get_all_series()
        if len(all_series) == 0:
            await discord_context.send('No series currently registered!')
            return

        await discord_context.send(embed=series_list_to_embed(all_series))
    else:
        series_obj = await _get_series(series)
        if series_obj is None:
            await discord_context.send(
                f'Sorry, it seems that series `{series}` wasn\'t found in our database.'
            )
        else:
            embed = await sync_to_async(series_to_embed)(series_obj)
            await discord_context.send(embed=embed)


__all__ = [
    'add',
    'remove',
    'update',
    '_list',
]
