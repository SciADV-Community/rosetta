import click

from .commands import add, remove, update, _list


@click.group()
@click.pass_context
def series(context):
    """Manage series operations"""
    pass


series.add_command(add)
series.add_command(remove)
series.add_command(update)
series.add_command(_list)


__all__ = [
    'series'
]
