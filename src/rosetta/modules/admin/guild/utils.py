from typing import TYPE_CHECKING
from datetime import datetime

from discord import Embed, Colour
from discord.utils import get

from playthrough.models import GameConfig

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
    ret.add_field(
        name='Category',
        value=str(config.category)
    )
    role = get(context.guild.roles, id=int(config.completion_role_id))
    ret.add_field(
        name='Role',
        value=f'{role.name} ({role.id})'
    )
    return ret
