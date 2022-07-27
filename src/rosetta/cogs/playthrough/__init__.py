import logging

import discord
from discord.ext import tasks
from discord.ext.commands import Converter

from rosetta.utils.db import (
    get_all_games_per_guild,
    get_existing_channel,
    get_game_config,
    set_channel_finished,
)

from .utils.channel import archive_channel
from .utils.roles import grant_completion_role, grant_meta_roles, remove_completion_role


class GameConfigConverter(Converter):
    async def convert(self, ctx: discord.ApplicationContext, argument: str):
        game_config = await get_game_config(ctx, argument)
        if not game_config:
            await ctx.interaction.response.send_message(
                f"{ctx.author.mention} Game does not exist, or it is not configured for this server.",
                ephemeral=True,
            )
            return
        return game_config


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
        ctx: discord.ApplicationContext,
        *,
        game: discord.Option(
            GameConfigConverter(),
            "The game's name.",
            autocomplete=game_autocomplete_playable,
        ),
    ):
        # Get game config
        if not game:
            return
        if not game.playable:
            return await ctx.response.send_message(
                f"No channel to drop for `{game.game}`; it's not playable.",
                ephemeral=True,
            )
        existing_channel = await get_existing_channel(ctx, game.game)
        if existing_channel:
            await ctx.response.defer(ephemeral=True)
            archive = await archive_channel(ctx, existing_channel)
            if not archive:
                return
            await ctx.followup.send("Your channel was archived!")

            message = f"And that's that. You dropped `{game.game}`."
            try:
                await ctx.followup.send(message, ephemeral=True)
            except Exception:
                await ctx.user.send(message)
        else:
            await ctx.response.send_message(
                f"You don't seem to have a channel for `{game.game}`."
            )

    @discord.slash_command(
        description="Finish playing a game. Grants completion role & archives any playthrough channel."
    )
    async def finished(
        self,
        ctx: discord.ApplicationContext,
        *,
        game: discord.Option(
            GameConfigConverter(), "The game's name.", autocomplete=game_autocomplete
        ),
    ):
        if not game:
            return
        existing_channel = await get_existing_channel(ctx, game.game)
        if existing_channel:
            await ctx.response.defer(ephemeral=True)
            archive = await archive_channel(ctx, existing_channel)
            if not archive:
                return
            await ctx.followup.send("Your channel was archived!")

            await set_channel_finished(existing_channel, True)

        await grant_completion_role(ctx, game)
        await grant_meta_roles(ctx, game)
        message = f"Hope you enjoyed {game.game}! You should now be able to see global spoiler channels!"
        try:
            await ctx.followup.send(message, ephemeral=True)
        except Exception as e:
            self.logger.error(e)
            print(e)
            await ctx.user.send(message)

    @discord.slash_command(
        description="Reset history on a certain game. Removes completion role."
    )
    async def reset(
        self,
        ctx: discord.ApplicationContext,
        *,
        game: discord.Option(
            GameConfigConverter(), "The game's name.", autocomplete=game_autocomplete
        ),
    ):
        if not game:
            return
        await remove_completion_role(ctx, game)
        await ctx.response.send_message(
            (
                f"Your progress on `{game.game}` has been reset. "
                "The completion role is removed!"
            ),
            ephemeral=True,
        )


def setup(client):
    client.add_cog(Playthrough(client))
