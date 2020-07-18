import click

from .game import game
from .channel import channel
from .series import series


@click.group()
@click.pass_context
def admin(context):
    """Command line tool for administration of the server."""
    pass


admin.add_command(game)
admin.add_command(channel)
admin.add_command(series)


__all__ = [
    'admin'
]
