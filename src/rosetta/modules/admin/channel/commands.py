import re

from asgiref.sync import sync_to_async
import click
from click import Context
from django.core.files import File
from discord.utils import get

from playthrough.models import Archive, Channel
from rosetta.utils.exporter import export_channel


@click.command()
@click.argument('channel', type=str)
@click.pass_context
async def archive(context: Context, channel: str):
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
        channel_obj = await sync_to_async(
            Channel.objects.filter(id=int(channel_id)).first
        )()
        if channel_obj is None:
            await discord_context.send(
                f'{channel} is seemingly not a playthrough channel.'
            )
            return

        exported_channel_file_path = export_channel(channel_id)
        exported_channel_file = File(
            file=open(exported_channel_file_path),
            name=exported_channel_file_path.name
        )
        channel_in_guild = get(discord_context.guild.channels, id=int(channel_id))
        await channel_in_guild.delete()
        await sync_to_async(Archive.objects.create)(
            channel=channel_obj,
            file=exported_channel_file
        )
        exported_channel_file.close()
        exported_channel_file_path.unlink()
        await discord_context.send('Archived the channel.')


__all__ = [
    'archive',
]
