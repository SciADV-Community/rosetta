#!env/bin/python3
"""Main module to run the bot."""
import logging
from asgiref.sync import sync_to_async
from os import path, mkdir
from discord.ext import commands
from playthrough.models import Guild
from rosetta import config, utils, checks

# Logging
if not path.isdir(config.LOG_ROOT):
    mkdir(config.LOG_ROOT )
logging.config.fileConfig(
    'logging.conf', defaults={'logfilename': config.LOG_ROOT / 'rosetta-log.log'})
logger = logging.getLogger(__name__)

# State
loaded_modules = []
client = commands.Bot(command_prefix=config.PREFIX, description=config.DESCRIPTION)


@client.event
async def on_ready():
    """Handle what happens when the bot is ready."""
    logger.info(f"Logged in as {client.user.name} - {client.user.id}")

    logger.info(f"------ Guilds ({len(client.guilds)}) ------")
    for guild in client.guilds:
        logger.info(guild.name)

    logger.info(f"------ Loading Modules ({len(config.INSTALLED_MODULES)}) ------")
    for module in config.INSTALLED_MODULES:
        if await utils.load_module(client, module):
            loaded_modules.append(module)


# Commands
@client.command(pass_context=True)
@checks.is_bot_admin()
async def load(context, module: str = None):
    """Load a module."""
    if not module:
        await context.send("Load requires the name of the module to load.")
    elif module not in loaded_modules:
        if await utils.load_module(client, module, context):
            loaded_modules.append(module)
    else:
        await context.send(f"Module `{module}` already loaded.")


# Unloading a module
@client.command(pass_context=True)
@checks.is_bot_admin()
async def unload(context, module: str = None):
    """Unload a module."""
    if not module:
        await context.send("Unload requires the name of the module to unload.")
    elif module in loaded_modules:
        if await utils.unload_module(client, module, context):
            loaded_modules.remove(module)
    else:
        await context.send(f"Module `{module}` not loaded.")


# Reloading a module
@client.command(pass_context=True)
@checks.is_bot_admin()
async def reload(context, module: str = None):
    """Reload a module."""
    if module:
        if module in loaded_modules:
            if await utils.unload_module(
                client, module, context
            ) and await utils.load_module(client, module, context):
                await context.send(f"`{module}` reload complete.")
        else:
            await context.send(f"Module `{module}` not loaded.")
    else:
        for module in loaded_modules:
            unloaded = await utils.unload_module(client, module, context)
            if unloaded:
                await utils.load_module(client, module, context)


@client.event
async def on_message(message):
    """Handle new messages."""
    if message.author is not client:
        await client.process_commands(message)


@client.event
async def on_command_error(context, error):
    """Handle error-handling from commands."""
    if type(error) != commands.errors.CheckFailure:
        command = context.message.content.split()[0][1:]
        logger.error("Error occurred for command %s: %s", command, error)


@client.event
async def on_guild_join(guild):
    """Handle setting up a new guild."""
    logger.info(f'Joined new guild: {guild.name} ({guild.id})')
    res = await sync_to_async(Guild.objects.get_or_create)(id=guild.id)
    logger.info(f'Registered Guild in the database: {res[0]} (created={res[1]}')


@client.event
async def on_guild_remove(guild):
    """Handle leaving a guild."""
    logger.info(f'Left guild: {guild.name} ({guild.id})')
    guild_obj = await sync_to_async(Guild.objects.get(id=guild.id).delete)()
    logger.info(f'Deleted Guild {guild_obj} from the database.')


# Running the client
client.run(config.TOKEN)
