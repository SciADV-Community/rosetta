from typing import List
import logging
from asgiref.sync import sync_to_async

import discord
from discord.ext import tasks
from discord.ext.commands import Cog, Converter
from discord.utils import get

from playthrough.models import MetaRoleConfig, GameConfig

from rosetta.cogs.admin.ui import ConfirmView
from rosetta.cogs.admin.utils import (
    get_existing_meta_role,
    validate_expr,
    create_meta_role_config,
    clean_expr,
    get_all_meta_roles_per_guild,
    get_meta_role,
)
from rosetta.cogs.playthrough.ui import GameButton
from rosetta.cogs.playthrough.utils.channel import archive_channel
from rosetta.utils import checks
from rosetta.utils.role_expr import MetaRoleEvaluator
from rosetta.utils.db import get_channel_in_db, set_channel_finished


class MetaRoleConverter(Converter):
    async def convert(self, ctx: discord.ApplicationContext, argument: str):
        meta_role_config = await get_meta_role(ctx.guild_id, argument)
        if not meta_role_config:
            await ctx.interaction.response.send_message(
                f"{ctx.author.mention} Meta Role does not exist!",
                ephemeral=True,
            )
            return
        return meta_role_config


class Admin(Cog):
    logger = logging.getLogger(__name__)

    def __init__(self, client):
        self.client = client
        self.logger.info(f"Cog {self.__class__.__name__} loaded successfully.")
        self.guild_meta_roles = {}
        self.cache.start()

    def meta_role_autocomplete(self, ctx: discord.AutocompleteContext) -> list[str]:
        mrs: List[str] = self.guild_meta_roles[ctx.interaction.guild_id]
        return [mr for mr in mrs if mr.lower().startswith(ctx.value.lower())]

    def cog_unload(self) -> None:
        self.cache.cancel()
        return super().cog_unload()

    @tasks.loop(minutes=5)
    async def cache(self):
        self.guild_meta_roles = await get_all_meta_roles_per_guild()

    admin = discord.SlashCommandGroup(
        "admin", "Administrative commands.", checks=[checks.is_bot_admin]
    )

    archive = admin.create_subgroup("archive", "Manual channel archival commands.")
    meta_role = admin.create_subgroup("meta-role", "Meta role commands.")

    @admin.command(
        description="Send a message containing the buttons to start playthrough channels."
    )
    async def send_game_buttons(
        self,
        ctx: discord.Interaction,
        channel: discord.Option(
            discord.TextChannel, "What channel should it be posted in?"
        ),
        game_order: discord.Option(
            str,
            "Provide the magic game order (comma separated game names).",
            default=None,
        ),
    ):
        # Get the view
        try:
            if game_order:
                game_order = game_order.split(",")
                assert type(game_order) == list
        except Exception as e:
            return await ctx.response.send_message(
                "Invalid game order. Check logs.", ephemeral=True
            )
        view = await GameButton.gen_button_view(self.client, ctx.guild.id, game_order)
        if view is None:
            return await ctx.response.send_message(
                "Sorry, couldn't create the buttons. Invalid game order most likely.",
                ephemeral=True,
            )

        # Send it to the designated channel
        await channel.send(
            "Click on one of the following buttons to start a channel!",
            view=view,
        )

        return await ctx.response.send_message("Done!", delete_after=3, ephemeral=True)

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
        channel_obj = await get_channel_in_db(channel)
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
            await set_channel_finished(channel_obj, True)

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

    @meta_role.command(description="Add a meta role to the server.")
    async def create(
        self,
        ctx: discord.ApplicationContext,
        name: discord.Option(str, "What should the role be called?"),
        logic: discord.Option(
            str,
            "Use @Role mentions and && for AND, || for OR, ! for not. Order with parenthesis.",
        ),
        colour: discord.Option(
            str,
            "What colour should this role be? (hex code)",
            default="#FFFFFF",
            required=False,
        ),
        existing_role_id: discord.Option(
            int,
            "Does the role have an existing ID? If so please provide it here",
            required=False,
        ),
    ):
        existing_meta_role = await get_existing_meta_role(name)
        if existing_meta_role:
            await ctx.followup.send(
                (
                    f"Meta role `{name}` is already added to the Guild.\n"
                    "Use `/admin meta-role update` to update its configuration."
                )
            )
            return
        logic = clean_expr(logic)
        game_configs, err = await validate_expr(logic)
        if err:
            await ctx.followup.send(f"Invalid expression: {err}")
            return
        if not existing_role_id:
            colour_rgb = tuple(
                int(colour.lstrip("#")[i : i + 2], 16) for i in (0, 2, 4)
            )
            colour = discord.Colour.from_rgb(*colour_rgb)
            role = await ctx.guild.create_role(name=name, colour=colour)
            existing_role_id = role.id
        await create_meta_role_config(
            name, colour, logic, ctx.guild_id, game_configs, existing_role_id
        )
        await ctx.followup.send(f"Added the `{name}` meta role!", ephemeral=True)

    @meta_role.command(
        description="Re-apply a Meta Role to the server."
    )
    async def reapply(
        self,
        ctx: discord.ApplicationContext,
        meta_role: discord.Option(
            MetaRoleConverter(),
            "The Meta Role.",
            autocomplete=meta_role_autocomplete,
        ),
    ):
        members = ctx.guild.members
        # Dry run
        members_to_add = []
        for member in members:
            user_role_ids = set([str(role.id) for role in member.roles])
            related_games = await sync_to_async(meta_role.games.all)()
            related_roles = [game.completion_role_id for game in related_games]
            evaluator_input = {
                role_id: role_id in user_role_ids for role_id in related_roles
            }
            evaluator = MetaRoleEvaluator(evaluator_input)
            result = evaluator.evaluate(meta_role.expression)
            if result:
                members_to_add.append(member)

        # Confirmation prompt
        view = ConfirmView(timeout=20)
        interaction = await ctx.response.send_message(
            f"Found {len(members_to_add)} members to add {meta_role.name} to. Are you sure you want to proceed?",
            view=view,
            ephemeral=True,
        )
        view.interaction = interaction
        await view.wait()
        if not view.value:
            return

        role_in_discord = get(ctx.guild.roles, id=int(meta_role.role_id))
        for member in members_to_add:
            await member.add_roles(role_in_discord)

        await ctx.followup.send(f"Re-applied the `{meta_role.name}` meta role!", ephemeral=True)


def setup(client):
    client.add_cog(Admin(client))
