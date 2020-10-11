import re
from typing import List, Union

from asgiref.sync import sync_to_async
import click
from click.core import Context
import discord
from discord.colour import Colour
from discord.utils import get
from django.db import IntegrityError

from playthrough.models import GameConfig, MetaRoleConfig
from rosetta.utils import ask
from rosetta.utils.role_expr import MetaRoleEvaluator


def _clean_expression(expression: str) -> str:
    """Clean the given expression.

    :param expression: The expression to clean.
    :return: The cleaned expression."""
    expression = re.sub(r'[<>@]', '', expression)
    expression = re.sub(r'&(\d+)', r'\1', expression)
    return expression


async def _validate_expression(
    context: discord.Context, expression: str
) -> Union[List[GameConfig], None]:
    """Check whether or not the given expression is valid.

    :param context: The Discord Context.
    :param expression: The expression to check.
    :return: Boolean of whether or not it's a valid expression."""
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
        await context.send(message)
        return None
    evaluator = MetaRoleEvaluator({_role_id: False for _role_id in role_ids})
    try:
        evaluator.evaluate(expression)
        return game_configs
    except Exception:
        await context.send((
            'The provided expression is invalid. Only use logical operators '
            'and role IDs / pings'
        ))
        return None


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
    expression = _clean_expression(expression)
    game_configs = await _validate_expression(expression)
    if game_configs is None:
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
@click.option('--yes', '-y', is_flag=True, help='confirm the removal')
@click.pass_context
async def remove(context: Context, name: str, yes: bool = False):
    """Remove a meta role."""
    discord_context = context.obj["discord_context"]
    existing_meta_role: MetaRoleConfig = await sync_to_async(
        MetaRoleConfig.objects.filter(name=name).first
    )()
    if existing_meta_role is None:
        await discord_context.send(
            (f'Meta role `{name}` not found.')
        )
        return
    if not yes:
        message = await ask(
            discord_context,
            f'Are you sure you want to remoe the meta_role {existing_meta_role}? (Y/N)',
            lambda m: m.content.lower() in ['y', 'n', 'yes', 'no']
        )
        if message is None:
            await discord_context.send('You forgot to reply! Will take that as a no.')
        else:
            if message.content.lower() in ['y', 'yes']:
                yes = True
            else:
                await discord_context.send('Alright then!')
    if yes:
        discord_context.guild.roles
        discord_role = get(discord_context.guild.roles, existing_meta_role.role_id)
        if discord_role is not None:
            await discord_role.delete()
        await existing_meta_role.delete()
        await discord_context.send(
            f'Poof! Meta role `{name}` is gone!'
        )


@meta_role.command()
@click.argument('name')
@click.option('--new-name', '-n', type=str, help='the new name of the role')
@click.option('--colour', '-c', type=str, help='hex code for the colour of the role')
@click.option('--expression', '-e', type=str, help='the condition to grant the role')
@click.option(
    '--role-id', '-r', type=str, help='the id of the meta role'
)
@click.pass_context
async def update(
    context: Context,
    name: str,
    new_name: str = None,
    expression: str = None,
    colour: str = None,
    role_id: str = None
):
    """Update a meta role."""
    discord_context = context.obj["discord_context"]
    existing_meta_role: MetaRoleConfig = await sync_to_async(
        MetaRoleConfig.objects.filter(name=name).first
    )()
    if existing_meta_role is None:
        await discord_context.send(
            (f'Meta role `{name}` not found.')
        )
        return
    if new_name is not None:
        try:
            existing_meta_role.name = new_name
            await sync_to_async(existing_meta_role.save)()
            await discord_context.send(f'Updated the name to {new_name}')
        except IntegrityError:
            await discord_context.send((
                f'Failed to update name to {new_name}. '
                'Perhaps it\'s already taken.'
            ))
            return
    if expression is not None:
        expression = _clean_expression(expression)
        new_game_configs = await _validate_expression(expression)
        if not new_game_configs:
            return
        existing_meta_role.expression = expression
        await sync_to_async(existing_meta_role.save)()
        await sync_to_async(existing_meta_role.games.clear)()
        await sync_to_async(existing_meta_role.games.add)(*new_game_configs)
        await discord_context.send('Updated the expression.')
    if colour is not None:
        existing_meta_role.colour = colour
        if not existing_meta_role.is_valid():
            await discord_context.send((
                f'Invalid colour `{colour}`.'
            ))
            return
        else:
            await sync_to_async(existing_meta_role.save)()
            await discord_context.send(f'Updated the colour to #{colour}.')  
    if role_id is not None:
        existing_meta_role.role_id = role_id
        await sync_to_async(existing_meta_role.save)()
        await discord_context.send(f'Updated the role to <@&{role_id}>')


@meta_role.command()
@click.pass_context
def list(context: Context):
    """List meta roles."""
    pass


__all__ = ['meta_role']
