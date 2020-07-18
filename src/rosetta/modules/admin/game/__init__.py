import click

from .commands import add, remove, update, _list


@click.group()
@click.pass_context
def game(context):
    """Manage game operations"""
    pass


game.add_command(add)
game.add_command(remove)
game.add_command(update)
game.add_command(_list)


__all__ = [
    'game'
]
