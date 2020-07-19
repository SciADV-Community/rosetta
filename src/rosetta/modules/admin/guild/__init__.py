import click

from .commands import add_game, remove_game, update_game


@click.group()
@click.pass_context
def guild(context):
    """Manage guild operations"""
    pass


guild.add_command(add_game)
guild.add_command(remove_game)
guild.add_command(update_game)


__all__ = [
    'guild'
]
