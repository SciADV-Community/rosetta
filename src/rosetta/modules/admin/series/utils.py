from typing import TYPE_CHECKING
from datetime import datetime

from discord import Embed, Colour

from playthrough.models import Series

if TYPE_CHECKING:
    from typing import List


def series_list_to_embed(series_list: 'List[Series]') -> Embed:
    """Utility function to convert a list of Series into an Embed.

    :return: An Embed displaying a List of Series."""
    ret = Embed(
        title='VN Database',
        type='rich',
        timestamp=datetime.now(),
        colour=Colour.gold()
    )
    series_str = ''
    for i, series in enumerate(series_list):
        series_str += f'{i + 1}) {series}\n'
    ret.add_field(name='Series', value=series_str)
    return ret


def series_to_embed(series: Series) -> Embed:
    """Utility function to convert a Series object into an Embed.

    :return: An Embed displaying a Series."""
    ret = Embed(
        title=series.name,
        type='rich',
        timestamp=datetime.now(),
        colour=Colour.gold()
    )
    ret.add_field(
        name='Aliases',
        value=', '.join([str(alias) for alias in series.aliases.all()])
    )
    return ret
