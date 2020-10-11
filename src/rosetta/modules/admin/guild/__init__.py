import click

from .game_commands import game
from .meta_role_commands import meta_role


@click.group()
@click.pass_context
def guild(context):
    """Manage guild operations"""
    pass


guild.add_command(game)
guild.add_command(meta_role)


__all__ = [
    'guild'
]
