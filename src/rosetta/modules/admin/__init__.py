import shlex
import click
import logging
from discord.ext.commands import Cog, command
from rosetta import checks

from .admin import admin


class Admin(Cog):
    logger = logging.getLogger(__name__)

    def __init__(self, client):
        self.client = client
        self.logger.info(f'Module {self.__class__.__name__} loaded successfully.')

    @command(pass_context=True)
    @checks.is_bot_admin()
    async def admin(self, context, *, args):
        """Admin command-line tool.

        Use 'admin --help' flag to get more info on it."""
        args = shlex.split(args)
        try:
            call = admin(args, standalone_mode=False, obj={'discord_context': context})
            status = await call if type(call) != int else call
            if status == 0:  # Click returns 0 if --help was called directly
                # Hack to get help at the right level
                target = admin
                info_name = f'{context.prefix}admin'
                with click.Context(target, info_name=info_name) as ctx:
                    for arg in args:
                        if arg != '--help' and not arg.startswith('-'):
                            target = target.get_command(ctx, arg)
                            info_name += f' {arg}'
                        else:
                            break

                # Get help string
                with click.Context(target, info_name=info_name) as ctx:
                    await context.send(f'```{target.get_help(ctx)}```')
        except click.exceptions.UsageError as e:
            self.logger.debug(e)
            await context.send(f'Incorrect command use: ```{e}```')
        except Exception as e:
            self.logger.debug(f'Exception occurred in admin command: {e}')
            await context.send(f'An error occurred when using the command: ```{e}```')


def setup(client):
    client.add_cog(Admin(client))
