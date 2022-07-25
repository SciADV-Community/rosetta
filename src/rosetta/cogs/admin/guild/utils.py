from typing import TYPE_CHECKING
from datetime import datetime

from discord import Embed, Colour
from discord.utils import get

from playthrough.models import GameConfig, MetaRoleConfig

if TYPE_CHECKING:
    from discord.ext.commands import Context
    from typing import List


def config_list_to_embed(config_list: 'List[GameConfig]') -> Embed:
    """Utility function to convert a list of GameConfig into an Embed.

    :return: An Embed displaying a List of Game Config."""
    ret = Embed(
        title='Active Games',
        type='rich',
        timestamp=datetime.now(),
        colour=Colour.gold()
    )
    config_str = ''
    for i, config in enumerate(config_list):
        config_str += f'{i + 1}) {config.game.name}\n'
    ret.add_field(name='Games', value=config_str)
    return ret


def game_config_to_embed(config: GameConfig, context: 'Context') -> Embed:
    """Utility function to convert a GameConfig object into an Embed.

    :return: An Embed displaying a GameConfig."""
    ret = Embed(
        title=str(config),
        type='rich',
        timestamp=datetime.now(),
        colour=Colour.gold()
    )
    role = get(context.guild.roles, id=int(config.completion_role_id))
    ret.add_field(
        name='Role',
        value=f'{role.name} ({role.id})'
    )
    return ret


def meta_role_to_embed(meta_role_config: MetaRoleConfig, context: 'Context') -> Embed:
    """Utility function to convert a `MetaRoleConfig` object into an embed.

    :return: An `Embed` displaying a `MetaRoleConfig`"""
    ret = Embed(
        title=str(meta_role_config),
        type='rich',
        timestamp=datetime.now(),
        colour=Colour.gold()
    )
    role = get(context.guild.roles, id=int(meta_role_config.role_id))
    ret.add_field(
        name='Role',
        value=f'{role.name} ({role.id})'
    )
    ret.add_field(
        name='Expression',
        value=meta_role_config.expression
    )
    # TODO Re-enable (ATM the problem is that for some reason these aren't pre-fetched)
    # ret.add_field(
    #     name='Games',
    #     value=', '.join([str(game) for game in meta_role_config.games.all()])
    # )
    return ret


def meta_roles_to_embed(meta_roles: 'List[MetaRoleConfig]') -> Embed:
    """Utility function to convert a list of MetaRoleConfig into an Embed.

    :return: An Embed displaying a List of MetaRoleConfig."""
    ret = Embed(
        title='Meta Roles',
        type='rich',
        timestamp=datetime.now(),
        colour=Colour.gold()
    )
    config_str = ''
    for i, meta_role in enumerate(meta_roles):
        config_str += f'{i + 1}) {meta_role}\n'
    ret.add_field(name='Meta Roles', value=config_str)
    return ret
