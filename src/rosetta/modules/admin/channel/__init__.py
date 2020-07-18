import click

from .commands import delete


@click.group()
@click.pass_context
def channel(context):
    """Manage channels"""
    pass


channel.add_command(delete)


__all__ = [
    'channel'
]
