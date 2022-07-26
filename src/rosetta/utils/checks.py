import logging

from discord import ApplicationContext

from rosetta.utils.db import get_user_from_author

logger = logging.getLogger(__name__)


async def is_bot_admin(ctx: ApplicationContext) -> bool:
    """A Pycord predicate to see if a user is a bot admin according to the db.

    :param context: the command invocation context. Mainly need the author.
    :return: whether or not the user is a bot admin.
    """
    user_obj = await get_user_from_author(ctx.author)
    is_admin = False
    if user_obj is not None:
        is_admin = user_obj.bot_admin
    if not is_admin:
        logger.info(
            "Unauthorized user %s attempted to invoke admin command.",
            ctx.author.name,
        )
        await ctx.interaction.response.send_message(
            (
                "You need bot-wide admin privileges "
                f"to use the `{ctx.command.name}` command."
            ),
            ephemeral=True,
        )
    return is_admin


__all__ = ["is_bot_admin"]
