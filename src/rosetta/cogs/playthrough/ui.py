import discord

from asgiref.sync import sync_to_async
from rosetta.cogs.playthrough.utils import get_instructions

from rosetta.cogs.playthrough.utils.roles import get_permissions

from .utils.db import (
    create_channel_in_db,
    get_meta_roles,
    get_playable_games,
    get_existing_channel,
)
from .utils.discord import get_channel_in_guild, get_game_completion_role
from .utils.channel import create_channel as create_channel_in_guild
from playthrough.models import GameConfig, MetaRoleConfig, Channel


class GameButton(discord.ui.Button):
    def __init__(
        self,
        *,
        game_config,
        style=discord.ButtonStyle.secondary,
        label=None,
        disabled=False,
        custom_id=None,
        url=None,
        emoji=None,
        row=None,
    ):
        super().__init__(
            style=style,
            label=label,
            disabled=disabled,
            custom_id=custom_id,
            url=url,
            emoji=emoji,
            row=row,
        )
        self.game_config = game_config

    def _get_channel_name(self, interaction: discord.Interaction, replay: bool):
        channel_name = (
            f"{interaction.user.display_name.lower()}"
            f"{self.game_config.game.channel_suffix.lower()}"
        )
        if replay:
            channel_name = channel_name.replace("plays", "replays")
        return channel_name

    async def _get_checks(self, interaction) -> tuple[bool, bool, Channel]:
        # Fetch player status
        existing_channel = await get_existing_channel(
            interaction, self.game_config.game
        )
        channel_in_guild = (
            get_channel_in_guild(interaction, existing_channel.id)
            if existing_channel
            else None
        )
        completion_role = get_game_completion_role(interaction, self.game_config)

        # Checks
        _has_finished_no_channel = (
            existing_channel and existing_channel.finished and not channel_in_guild
        )
        _has_active_channel = existing_channel and channel_in_guild
        _has_completion_role = completion_role in interaction.user.roles

        replay = _has_completion_role and (
            _has_finished_no_channel or not existing_channel
        )

        return replay, _has_active_channel, existing_channel

    async def callback(self, interaction: discord.Interaction):
        # checks
        replay, _has_active_channel, existing_channel = await self._get_checks(
            interaction
        )

        if _has_active_channel:
            return await interaction.response.send_message(
                f"You already have a channel for {self.game_config.game}.",
                ephemeral=True,
            )

        # Channel details
        channel_name = self._get_channel_name(interaction, replay)
        meta_role_id = await MetaRoleSelect.ask_for_meta_role(
            interaction, self.game_config
        )
        if type(meta_role_id) is bool and meta_role_id is False:
            return

        permissions = await get_permissions(interaction, self.game_config, meta_role_id)

        # Try creating the channel on discord
        channel = await create_channel_in_guild(
            interaction, self.game_config, channel_name, permissions
        )
        if channel is None:
            return

        # Create the channel on the DB
        if existing_channel:
            await sync_to_async(existing_channel.update_id)(channel.id)
        else:
            await create_channel_in_db(
                interaction, self.game_config, channel.id, finished=replay
            )

        # Send instructions
        instructions_msg = await channel.send(get_instructions(self.game_config))
        await channel.send(interaction.user.mention)
        await instructions_msg.pin()

        # Closing statement
        try:
            await interaction.response.send_message(
                content=f"Successfully created your channel: {channel.mention}, have fun!",
                ephemeral=True,
                delete_after=8,
            )
        except discord.errors.InteractionResponded:
            await interaction.edit_original_message(
                content=f"Successfully created your channel: {channel.mention}, have fun!",
                view=None,
            )
            await interaction.delete_original_message(delay=8)

    @classmethod
    async def gen_button_view(cls, client, guild_id):
        game_configs = await get_playable_games(guild_id)

        view = discord.ui.View(timeout=None)

        for i, game_config in enumerate(game_configs):
            emoji = client.get_emoji(int(game_config.emoji))
            game_button = cls(
                game_config=game_config,
                label=game_config.game.name,
                custom_id=game_config.game.slug,
                emoji=emoji,
                row=i // 5,
            )
            view.add_item(game_button)

        return view


class MetaRoleSelect(discord.ui.View):
    class _Select(discord.ui.Select):
        async def callback(self, interaction: discord.Interaction):
            meta_role_id = self.values[0]
            if meta_role_id == "None":
                meta_role_id = None
            await self.view.picked_option(meta_role_id)

    def __init__(self, *items, meta_roles: list[MetaRoleConfig], timeout=20):
        super().__init__(*items, timeout=timeout)
        options = options = [discord.SelectOption(label="None", value="None")] + [
            discord.SelectOption(label=meta_role.name, value=meta_role.role_id)
            for meta_role in meta_roles
        ]
        self.add_item(self._Select(options=options))

    async def on_timeout(self) -> None:
        self.children[0].disabled = True
        await self.interaction.edit_original_message(view=self)
        self.value = False

    async def picked_option(self, meta_role_id: int):
        self.value = meta_role_id
        self.children[0].disabled = True
        await self.interaction.edit_original_message(view=self)
        self.stop()

    @classmethod
    async def ask_for_meta_role(
        cls,
        ctx: discord.Interaction,
        game_config: GameConfig,
    ):
        meta_roles = await get_meta_roles(game_config)
        if len(meta_roles) > 0:
            select = cls(meta_roles=meta_roles)
            select.interaction = await ctx.response.send_message(
                "Would you like to lock the channel behind a Meta-Role? If not or unsure, select `None`.",
                view=select,
                ephemeral=True,
                delete_after=15,
            )
            await select.wait()
            return select.value
        else:
            return None
