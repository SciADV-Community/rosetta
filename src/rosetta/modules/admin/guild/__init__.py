import click

from .game_commands import game


@click.group()
@click.pass_context
def guild(context):
    """Manage guild operations"""
    pass


guild.add_command(game)


__all__ = [
    'guild'
]
