import re

from asgiref.sync import sync_to_async
import click
from click.core import Context
from discord.colour import Colour

from playthrough.models import GameConfig, MetaRoleConfig
from rosetta.utils.role_expr import MetaRoleEvaluator


@click.group()
@click.pass_context
def meta_role(context: Context):
    """Manage meta role operations."""
    pass


@meta_role.command()
@click.option('--name', '-n', type=str, help='the name of the role', required=True)
@click.option(
    '--expression', '-e', type=str, help='the condition to grant the role',
    required=True
)
@click.option('--colour', '-c', type=str, help='hex code for the colour of the role')
@click.option('--create-role', '-cr', is_flag=True, help='create the meta role')
@click.option(
    '--role-id', '-r', type=str, help='the id of the meta role'
)
@click.pass_context
async def add(
    context: Context,
    name: str,
    expression: str,
    colour: str = None,
    create_role: bool = False,
    role_id: str = None
):
    """Add a new meta role."""
    discord_context = context.obj["discord_context"]
    existing_meta_role = await sync_to_async(
        MetaRoleConfig.objects.filter(name=name).first
    )()
    if existing_meta_role:
        await discord_context.send(
            (f'Meta role `{name}` is already added to the Guild.\n'
             'Use `meta-role update` to update its configuration.')
        )
        return
    expression = re.sub(r'[<>@]', '', expression)
    expression = re.sub(r'&(\d+)', r'\1', expression)
    role_ids = re.findall(r'\d+', expression)
    game_configs = []
    unconfigured_games = []
    for _role_id in role_ids:
        game_config = await sync_to_async(GameConfig.objects.filter(
            completion_role_id=_role_id
        ).first)()
        if game_config is not None:
            game_configs.append(game_config)
        else:
            unconfigured_games.append(_role_id)
    if len(game_configs) != len(role_ids):
        message = 'Could not find configured games for: '
        message += str(', '.join(
            [f'<@&{_role_id}>' for _role_id in unconfigured_games]
        ))
        await discord_context.send(message)
        return
    evaluator = MetaRoleEvaluator({_role_id: False for _role_id in role_ids})
    try:
        evaluator.evaluate(expression)
    except Exception:
        await discord_context.send((
            'The provided expression is invalid. Only use logical operators '
            'and role IDs / pings'
        ))
        return
    if not create_role and role_id is None:
        await discord_context.send((
            'You have not provided a role id or enabled the create role flag (-cr).'
            'Please provide one.'
        ))
        return
    meta_role_config = MetaRoleConfig(
        name=name,
        colour=colour,
        expression=expression,
        guild_id=discord_context.guild.id
    )
    if create_role:
        role_colour = None
        if meta_role_config.colour is not None:
            role_colour = Colour.from_rgb(*meta_role_config.get_colour_as_rgb())
        discord_role = await discord_context.guild.create_role(
            name=name, colour=role_colour
        )
        meta_role_config.role_id = discord_role.id
    await sync_to_async(meta_role_config.save)()
    await sync_to_async(meta_role_config.games.add)(*game_configs)
    await discord_context.send(
        f'Added the `{name}` meta role!'
    )


@meta_role.command()
@click.argument('name', type=str)
@click.pass_context
def remove(context: Context, name: str):
    """Remove a meta role."""
    pass


@meta_role.command()
@click.argument('name')
@click.option('--new-name', '-n', type=str, help='the new name of the role')
@click.option('--colour', '-c', type=str, help='hex code for the colour of the role')
@click.option('--expression', '-e', type=str, help='the condition to grant the role')
@click.option(
    '--role-id', '-r', type=str, help='the id of the meta role'
)
@click.pass_context
def update(
    context: Context,
    name: str,
    new_name: str = None,
    colour: str = None,
    role_id: str = None
):
    """Update a meta role."""
    pass


@meta_role.command()
@click.pass_context
def list(context: Context):
    """List meta roles."""
    pass


__all__ = ['meta_role']
