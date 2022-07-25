import logging

import discord
from asgiref.sync import sync_to_async
from discord.ext import tasks

from .utils.channel import archive_channel
from .utils.db import (
    get_all_games_per_guild,
    get_existing_channel,
    get_game_config,
)
from .utils.roles import (
    grant_completion_role,
    grant_meta_roles,
    remove_completion_role,
)

from .ui import GameButton


class Playthrough(discord.Cog):
    logger = logging.getLogger(__name__)

    def __init__(self, client):
        self.client = client
        self.logger.info(f"Cog {self.__class__.__name__} loaded successfully.")
        # Cache
        self.guild_games = {}
        self.cache.start()

    def game_autocomplete(self, ctx: discord.AutocompleteContext) -> list[str]:
        gcs = self.guild_games[ctx.interaction.guild_id]
        return [
            gc.game.name
            for gc in gcs
            if gc.game.name.lower().startswith(ctx.value.lower())
        ]

    def game_autocomplete_playable(self, ctx: discord.AutocompleteContext) -> list[str]:
        gcs = self.guild_games[ctx.interaction.guild_id]
        return [
            gc.game.name
            for gc in gcs
            if gc.game.name.lower().startswith(ctx.value.lower()) and gc.playable
        ]

    def cog_unload(self) -> None:
        self.cache.cancel()
        return super().cog_unload()

    @tasks.loop(minutes=5)
    async def cache(self):
        self.guild_games = await get_all_games_per_guild()

    @discord.slash_command(description="Drop a game. Closes playthrough channel.")
    async def drop(
        self,
        ctx,
        *,
        game: discord.Option(
            str, "The game's name.", autocomplete=game_autocomplete_playable
        ),
    ):
        # Get game config
        game_config = await get_game_config(ctx, game)
        if not game_config:
            return await ctx.response.send_message(
                ("Game does not exist, or it is not configured for this server.")
            )
        if not game_config.playable:
            return await ctx.response.send_message(
                (f"No channel to drop for `{game_config.game}`; it's not playable.")
            )
        existing_channel = await get_existing_channel(ctx, game_config.game)
        if existing_channel:
            await ctx.response.defer(ephemeral=True)
            archive = await archive_channel(ctx, existing_channel)
            if not archive:
                return
            await ctx.followup.send("Your channel was archived!", delete_after=8)

            message = f"And that's that. You dropped `{game_config.game}`."
            try:
                await ctx.followup.send(message, ephemeral=True, delete_after=8)
            except Exception:
                await ctx.user.send(message)
        else:
            await ctx.response.send_message(
                f"You don't seem to have a channel for `{game_config.game}`."
            )

    @discord.slash_command(
        description="Finish playing a game. Grants completion role & archives any playthrough channel."
    )
    async def finished(
        self,
        ctx,
        *,
        game: discord.Option(str, "The game's name.", autocomplete=game_autocomplete),
    ):
        # Get game config
        game_config = await get_game_config(ctx, game)
        if not game_config:
            return await ctx.response.send_message(
                ("Game does not exist, or it is not configured for this server."),
                ephemeral=True,
            )

        existing_channel = await get_existing_channel(ctx, game_config.game)
        if existing_channel:
            await ctx.response.defer(ephemeral=True)
            archive = await archive_channel(ctx, existing_channel)
            if not archive:
                return
            await ctx.followup.send("Your channel was archived!", delete_after=8)

            existing_channel.finished = True
            await sync_to_async(existing_channel.save)()

        await grant_completion_role(ctx, game_config)
        await grant_meta_roles(ctx, game_config)
        message = f"Hope you enjoyed {game_config.game}! You should now be able to see global spoiler channels!"
        try:
            await ctx.followup.send(message, ephemeral=True, delete_after=8)
        except Exception:
            await ctx.user.send(message)

    @discord.slash_command(
        description="Reset history on a certain game. Removes completion role."
    )
    async def reset(
        self,
        ctx,
        *,
        game: discord.Option(str, "The game's name.", autocomplete=game_autocomplete),
    ):
        # Get game config
        game_config = await get_game_config(ctx, game)
        if not game_config:
            return await ctx.response.send_message(
                "Game does not exist, or it is not configured for this server.",
                ephemeral=True,
                delete_after=8,
            )
        await remove_completion_role(ctx, game_config)
        await ctx.response.send_message(
            (
                f"Your progress on `{game_config.game}` has been reset. "
                "The completion role is removed!"
            ),
            ephemeral=True,
            delete_after=8,
        )
        pass


def setup(client):
    client.add_cog(Playthrough(client))
