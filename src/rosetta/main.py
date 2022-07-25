#!env/bin/python3
"""Main module to run the bot."""
import logging

import discord
from asgiref.sync import sync_to_async
from playthrough.models import Guild

from rosetta import config
from rosetta.cogs.playthrough.ui import gen_button_view

# Logging
if not config.LOG_ROOT.exists():
    config.LOG_ROOT.mkdir(parents=True)

logging.config.fileConfig(
    "logging.conf", defaults={"logfilename": config.LOG_ROOT / "rosetta-log.log"}
)
logger = logging.getLogger(__name__)


class Rosetta(discord.Bot):
    COGS = ["admin", "playthrough"]

    def __init__(self, description=None, *args, **options):
        super().__init__(description, *args, **options)

        # Load cogs
        extensions = [f"rosetta.cogs.{cog}" for cog in self.COGS]
        self.load_extensions(*extensions)

    async def on_ready(self):
        """Handle what happens when the bot is ready."""
        logger.info(f"Logged in as {client.user.name} - {client.user.id}")
        logger.info(f"------ Guilds ({len(client.guilds)}) ------")
        for guild in client.guilds:
            logger.info(guild.name)

            # Persistent UI
            playthrough_button_view = await gen_button_view(self, guild.id)
            self.add_view(playthrough_button_view)

    async def on_guild_join(self, guild: discord.Guild):
        """Handle setting up a new guild."""
        logger.info(f"Joined new guild: {guild.name} ({guild.id})")
        res = await sync_to_async(Guild.objects.get_or_create)(id=str(guild.id))
        res[0].name = guild.name
        await sync_to_async(res[0].save)()
        logger.info(f"Registered Guild in the database: {res[0]} (created={res[1]})")

    async def on_application_command_error(
        self, ctx: discord.ApplicationContext, error: discord.DiscordException
    ):
        logger.error("Error occurred for command %s: %s", ctx.command, error)


# Intents
# TODO proper research on this
intents = discord.Intents.default()
intents.members = True
intents.message_content = True
# intents.guilds = True
# intents.guild_messages = True
# intents.emojis = True
# intents.message_content = True

# Running the client
client = Rosetta(
    description=config.DESCRIPTION,
    intents=intents,
    debug_guilds=[1000511745548365925],
)
client.run(config.TOKEN)
