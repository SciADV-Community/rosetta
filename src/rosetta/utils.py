"""Module with various utilities for the bot."""
import logging
from typing import TYPE_CHECKING

from asgiref.sync import sync_to_async

from playthrough.models import User

if TYPE_CHECKING:
    from discord import Message
    from discord import User as DiscordUser
    from discord.ext.commands import Context
    from typing import Callable, Union


logger = logging.getLogger(__name__)


async def send_message(context, message):  # pragma: no cover
    """Send a message if the the provided context is not None."""
    if context:
        await context.send(message)


@sync_to_async
def is_bot_admin(author: 'DiscordUser') -> bool:
    """Checks whether or not the discord user is a bot admin.

    :return: Whether or not the user is a bot admin."""
    user_obj = User.objects.filter(id=author.id)
    ret = False
    if user_obj.exists():
        ret = user_obj[0].bot_admin

    return ret


async def load_module(client, module, context=None):  # pragma: no cover
    """Load a certain module. Returns whether or not the loading succeeded."""
    if context and not await is_bot_admin(context.author):
        logger.warning(
            "Unauthorized user %s attempted to load module %s",
            context.author.name,
            module,
        )
        await send_message(context, "You are not authorized to load modules.")
        return False

    try:
        module = f"rosetta.{module}"
        client.load_extension(module)
        logger.info("Module %s was successfully loaded.", module)
        await send_message(context, f"{module} was successfully loaded.")
        return True
    except (AttributeError, ImportError) as e:
        logger.error("Failed to load module %s: %s", module, e)
        await send_message(
            context,
            f"{module} could not be loaded due to an error. Please check the logs.",
        )
        return False


async def unload_module(client, module, context=None):  # pragma: no cover
    """Unload a certain module. Returns whether or not the unloading succeeded."""
    if context and not await is_bot_admin(context.author):
        logger.warning(
            "Unauthorized user %s attempted to unload module %s",
            context.author.name,
            module,
        )
        await send_message(context, "You are not authorized to unload modules.")
        return False

    try:
        module = f"rosetta.{module}"
        client.unload_extension(module)
        logger.info("Module %s was successfully unloaded.", module)
        await send_message(context, f"{module} was successfully unloaded.")
        return True
    except (AttributeError, ImportError) as e:
        logger.error("Failed to unload module %s: %s", module, e)
        await send_message(
            context,
            f"{module} could not be unloaded due to an error. Please check the logs.",
        )
        return False


async def ask(
    context: 'Context',
    prompt: str,
    condition: 'Callable[[Message],bool]',
    timeout: int = 15
) -> 'Union[Message,None]':
    """Utility to make dialogues easier.

    :param context: The discord context.
    :param prompt: The prompt to send.
    :param condition: The condition to accept new messages.
    :param timeout: (Optional) the timeout to wait for. Defaults to 15s.
    :return: The first Message matched or None."""
    def check(m: 'Message') -> bool:
        cond1 = condition(m)
        return cond1 and m.channel == context.channel

    prompt_msg = await context.send(prompt)
    await context.bot.wait_for('message', check=check, timeout=timeout)
    await prompt_msg.delete()
