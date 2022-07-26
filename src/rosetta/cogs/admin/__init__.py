import logging

import discord
from discord.ext.commands import Cog

from rosetta.cogs.admin.ui import ConfirmView
from rosetta.cogs.playthrough.ui import GameButton
from rosetta.cogs.playthrough.utils.channel import archive_channel
from rosetta.utils import checks
from rosetta.utils.db import get_channel_in_db, set_channel_finished


class Admin(Cog):
    logger = logging.getLogger(__name__)

    def __init__(self, client):
        self.client = client
        self.logger.info(f"Cog {self.__class__.__name__} loaded successfully.")

    admin = discord.SlashCommandGroup(
        "admin", "Administrative commands.", checks=[checks.is_bot_admin]
    )

    archive = admin.create_subgroup("archive", "Manual channel archival commands.")

    @admin.command(
        description="Send a message containing the buttons to start playthrough channels."
    )
    async def send_game_buttons(
        self,
        ctx: discord.Interaction,
        channel: discord.Option(
            discord.TextChannel, "What channel should it be posted in?"
        ),
    ):
        # Get the view
        view = await GameButton.gen_button_view(self.client, ctx.guild.id)

        # Send it to the designated channel
        await channel.send(
            "Click on one of the following buttons to start a channel!",
            view=view,
        )

        await ctx.response.send_message("Done!", delete_after=3, ephemeral=True)

    @archive.command(description="Archive a channel.")
    async def channel(
        self,
        ctx: discord.Interaction,
        channel: discord.Option(
            discord.TextChannel, "What channel should be archived?"
        ),
        finished: discord.Option(bool, "Is this channel finished?", default=False),
    ):
        # Get the channel in the DB
        channel_obj = get_channel_in_db(channel)
        if channel_obj is None:
            return await ctx.response.send_message(
                f"{channel.mention} is seemingly not a playthrough channel."
            )

        # Archive it
        await ctx.defer(ephemeral=True)
        archive = await archive_channel(ctx, channel_obj)
        if not archive:
            return

        # Set finished status
        if finished:
            await set_channel_finished(channel, True)

        await ctx.followup.send("The channel was archived!", delete_after=8)

    @archive.command(description="Archive a category of channels.")
    async def category(
        self,
        ctx: discord.ApplicationContext,
        category: discord.Option(
            discord.CategoryChannel, "What category should be archived?"
        ),
        finished: discord.Option(bool, "Is this channel finished?", default=False),
    ):
        # Get the channels
        category_channels = category.text_channels

        # Confirmation prompt
        view = ConfirmView(timeout=20)
        interaction = await ctx.response.send_message(
            f"Found {len(category_channels)} channels in {category.name} to archive. Are you sure you want to proceed?",
            view=view,
            ephemeral=True,
        )
        view.interaction = interaction
        await view.wait()
        if not view.value:
            return

        # Archive each channel
        for i, channel in enumerate(category_channels):
            try:
                channel_obj = await get_channel_in_db(channel)
                archive = await archive_channel(ctx, channel_obj)
                if archive:
                    if finished:
                        await set_channel_finished(channel, True)
                    await interaction.edit_original_message(
                        content=f"Archived {channel.name} ({i+1}/{len(category_channels)})",
                        view=None,
                    )
            except Exception as e:
                await interaction.edit_original_message(
                    content=f"Failed to archive {channel.name}. Skipping...\n```{e}```",
                    view=None,
                )


def setup(client):
    client.add_cog(Admin(client))
