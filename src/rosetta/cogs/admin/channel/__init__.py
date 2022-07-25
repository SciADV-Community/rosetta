import click

from .commands import archive, archive_category


@click.group()
@click.pass_context
def channel(context):
    """Manage series operations"""
    pass


channel.add_command(archive)
channel.add_command(archive_category)


__all__ = [
    'channel'
]
