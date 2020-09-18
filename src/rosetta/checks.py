import logging
from typing import TYPE_CHECKING

from asgiref.sync import sync_to_async
from discord.ext.commands import check

from playthrough.models import User

if TYPE_CHECKING:
    from discord.ext.commands import Context


logger = logging.getLogger(__name__)


def is_bot_admin():
    """Discord.py check if the user is a bot admin.

    :return: User admin check."""
    async def predicate(context: 'Context') -> bool:
        user_obj = await sync_to_async(
            User.objects.filter(id=context.author.id).first
        )()
        is_admin = False
        if user_obj is not None:
            is_admin = user_obj.bot_admin
        if not is_admin and context.invoked_with != 'help':
            logger.info(
                'Unauthorized user %s attempted to invoke admin command.',
                context.author.name
            )
            await context.send((
                'You need bot-wide admin privileges '
                f'to use the `{context.command.name}` command.'
            ))
        return is_admin
    return check(predicate)


__all__ = [
    'is_bot_admin'
]
