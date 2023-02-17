#!env/bin/python3
"""Main module to run the bot."""
import logging

import discord

from rosetta import config
from rosetta.cogs.playthrough.ui import GameButton
from rosetta.utils.db import get_or_create_guild

# Logging
if not config.LOG_ROOT.exists():
    config.LOG_ROOT.mkdir(parents=True)

logging.config.fileConfig(
    "logging.conf", defaults={"logfilename": config.LOG_ROOT / "rosetta-log.log"}
)
logger = logging.getLogger(__name__)


class Rosetta(discord.Bot):
    """The main Bot class for Rosetta!"""

    COGS = ["admin", "playthrough"]

    def __init__(self, description=None, *args, **options):
        """The main Bot class for Rosetta!

        :param description: The bot description.
        """
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
            try:
                playthrough_button_view = await GameButton.gen_button_view(
                    self, guild.id
                )
                self.add_view(playthrough_button_view)
            except TypeError:
                logger.warning(f"No emojis for games in {guild.name}, skipping...")

    async def on_guild_join(self, guild: discord.Guild):
        """Handle setting up a new guild."""
        logger.info(f"Joined new guild: {guild.name} ({guild.id})")
        res = await get_or_create_guild(guild)
        logger.info(f"Registered Guild in the database: {res[0]} (created={res[1]})")

    async def on_application_command_error(
        self, ctx: discord.ApplicationContext, error: discord.DiscordException
    ):
        """Handle errors globally."""
        logger.error("Error occurred for command %s: %s", ctx.command, error)


# Intents
# TODO proper research on this
intents = discord.Intents.default()
intents.members = True
intents.message_content = True

# Running the client
client = Rosetta(
    description=config.DESCRIPTION,
    intents=intents,
    debug_guilds=[1000511745548365925],
)
client.run(config.TOKEN)
