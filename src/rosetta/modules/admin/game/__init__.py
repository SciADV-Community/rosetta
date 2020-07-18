import click

from .commands import add, remove


@click.group()
@click.pass_context
def game(context):
    """Manage game operations"""
    pass


game.add_command(add)
game.add_command(remove)


__all__ = [
    'game'
]
