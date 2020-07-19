from typing import TYPE_CHECKING
from datetime import datetime

from discord import Embed, Colour

from playthrough.models import Game

if TYPE_CHECKING:
    from typing import List


def games_list_to_embed(games_list: 'List[Game]') -> Embed:
    """Utility function to convert a list of Games into an Embed.

    :return: An Embed displaying a List of Games."""
    ret = Embed(
        title='VN Database',
        type='rich',
        timestamp=datetime.now(),
        colour=Colour.gold()
    )
    games_str = ''
    for i, game in enumerate(games_list):
        games_str += f'{i + 1}) {game}\n'
    ret.add_field(name='Games', value=games_str)
    return ret


def game_to_embed(game: Game) -> Embed:
    """Utility function to convert a Series object into an Embed.

    :return: An Embed displaying a Series."""
    ret = Embed(
        title=game.name,
        type='rich',
        timestamp=datetime.now(),
        colour=Colour.gold()
    )
    ret.add_field(
        name='Series',
        value=str(game.series)
    )
    aliases = game.aliases.all()
    if len(aliases) > 0:
        ret.add_field(
            name='Aliases',
            value=', '.join([str(alias) for alias in aliases])
        )
    ret.add_field(
        name='Channel Suffix',
        value=game.channel_suffix,
        inline=False
    )
    ret.add_field(
        name='Role Template',
        value=str(game.completion_role),
        inline=False
    )
    return ret
