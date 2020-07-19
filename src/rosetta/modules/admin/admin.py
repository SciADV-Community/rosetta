import click

from .game import game
from .series import series
from .guild import guild


@click.group()
@click.pass_context
def admin(context):
    """Command line tool for administration of the server."""
    pass


admin.add_command(game)
admin.add_command(series)
admin.add_command(guild)


__all__ = [
    'admin'
]
