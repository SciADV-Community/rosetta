import re

from asgiref.sync import sync_to_async
import click
from click import Context as ClickContext
from django.core.files import File
from discord.utils import get
from discord.ext.commands import Context as DiscordContext

from playthrough.models import Archive, Channel
from rosetta.utils import ask
from rosetta.utils.exporter import export_channel


async def archive_channel(context: DiscordContext, channel_id: str, finished: bool = False):
    """Archives a certain channel.

    :param context: The Discord Context.
    :param channel_id: The ID of the channel to archive."""
    channel_obj = await sync_to_async(
        Channel.objects.filter(id=int(channel_id)).first
    )()
    if channel_obj is None:
        await context.send(
            f'<#{channel_id}> is seemingly not a playthrough channel.'
        )
        return
    await context.send(f'Archiving <#{channel_id}>...')
    exported_channel_file_path = export_channel(channel_id)
    exported_channel_file = File(
        file=open(exported_channel_file_path),
        name=exported_channel_file_path.name
    )
    channel_in_guild = get(context.guild.channels, id=int(channel_id))
    await channel_in_guild.delete()
    await sync_to_async(Archive.objects.create)(
        channel=channel_obj,
        file=exported_channel_file
    )
    exported_channel_file.close()
    exported_channel_file_path.unlink()
    if finished:
        channel_obj.finished = finished
        await sync_to_async(channel_obj.save)()
    await context.send('Archived the channel.')


@click.command()
@click.argument('channel', type=str)
@click.option('--finished', '-f', is_flag=True, help='Whether or not the channels here are finished')
@click.pass_context
async def archive(context: ClickContext, channel: str, finished: bool = False):
    """Command to archive a channel"""
    discord_context = context.obj["discord_context"]
    channel_match = re.match(r'<#(\d+)>', channel)
    if not channel_match:
        await discord_context.send(
            f'Invalid channel: `{channel}`, are you not tagging it with `#`?'
        )
        return

    channel_id = channel_match.group(1)

    async with discord_context.typing():
        await archive_channel(context, channel_id, finished)


@click.command()
@click.argument('category-id', type=int)
@click.option('--finished', '-f', is_flag=True, help='Whether or not the channels here are finished')
@click.option('--yes', '-y', is_flag=True, help='skips the confirmation prompt')
@click.pass_context
async def archive_category(
    context: ClickContext, category_id: int, finished: bool = False, yes: bool = False
):
    """Command to archive a category"""
    discord_context = context.obj["discord_context"]
    category_in_guild = get(discord_context.guild.categories, id=category_id)
    if not category_in_guild:
        await discord_context.send(f'Category with id {category_id} not found.')
        return
    category_channels = category_in_guild.text_channels
    await discord_context.send(
        f'Found {len(category_channels)} channels in {category_in_guild.name} to archive.'
    )
    if not yes:
        # TODO Put this thing into its own utility function for reuse
        message = await ask(
            discord_context,
            'Continue? (Y/N)',
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
        for i, channel in enumerate(category_channels):
            await discord_context.send(f'Archiving {channel.name} ({i}/{len(category_channels)})')
            try:
                await archive_channel(discord_context, channel.id, finished)
            except Exception as e:
                await discord_context.send(f'Failed to archive {channel.name}. Skipping...')
                await discord_context.send(f'```{e}```')
        await discord_context.send(f'Finished archiving category {category_id}.')


__all__ = [
    'archive',
    'archive_category',
]
