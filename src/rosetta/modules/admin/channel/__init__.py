import click

from .commands import archive


@click.group()
@click.pass_context
def channel(context):
    """Manage series operations"""
    pass


channel.add_command(archive)


__all__ = [
    'channel'
]
