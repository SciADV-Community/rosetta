import click

from .commands import (
    add, remove, update, _list, set_role_template, remove_role_template
)


@click.group()
@click.pass_context
def game(context):
    """Manage game operations"""
    pass


game.add_command(add)
game.add_command(remove)
game.add_command(update)
game.add_command(_list)
game.add_command(set_role_template)
game.add_command(remove_role_template)


__all__ = [
    'game'
]
