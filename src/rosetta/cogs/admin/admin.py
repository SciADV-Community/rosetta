import click

from .game import game
from .series import series
from .guild import guild
from .channel import channel


@click.group()
@click.pass_context
def admin(context):
    """Command line tool for administration of the server."""
    pass


admin.add_command(game)
admin.add_command(series)
admin.add_command(guild)
admin.add_command(channel)


__all__ = [
    'admin'
]
