import discord

from playthrough.models import Channel, GameConfig, MetaRoleConfig

from rosetta.cogs.playthrough.utils import get_instructions
from rosetta.cogs.playthrough.utils.roles import get_channel_permissions
from rosetta.utils.db import (
    create_channel_in_db,
    get_existing_channel,
    get_meta_roles,
    get_playable_games,
    update_channel_id,
)

from .utils.channel import create_channel as create_channel_in_guild
from .utils.discord import get_channel_in_guild, get_game_completion_role


class GameButton(discord.ui.Button):
    """Class to represent a Button for starting a channel for a given Game."""

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
        """Class to represent a Button for starting a channel for a given Game.

        :param game_config: the GameConfig to generate the button for.
        """
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

    def _get_channel_name(self, ctx: discord.Interaction, replay: bool) -> str:
        """Get the channel name based on the Interaction context.

        :param ctx: the Interaction context.
        :param replay: whether or not this is a replay channel.
        :return: the channel name.
        """
        channel_name = (
            f"{ctx.user.display_name.lower()}"
            f"{self.game_config.game.channel_suffix.lower()}"
        )
        if replay:
            channel_name = channel_name.replace("plays", "replays")
        return channel_name

    async def _get_checks(self, ctx: discord.Interaction) -> tuple[bool, bool, Channel]:
        """Get screening information for a given interaction as far as the channel goes.
        Check if this is a replay, if the user already has an active channel, and fetch db info.

        :param ctx: the Interaction context.
        :return: a tuple of whether or not this is a replay, whether or not there is a channel, and the db info
        """
        # Fetch player status
        existing_channel, channel_in_guild = await get_existing_channel(
            ctx, self.game_config.game
        )
        completion_role = get_game_completion_role(ctx, self.game_config)

        # Checks
        _has_finished_no_channel = (
            existing_channel and existing_channel.finished and not channel_in_guild
        )
        _has_active_channel = existing_channel and channel_in_guild
        _has_completion_role = completion_role in ctx.user.roles

        replay = _has_completion_role and (
            _has_finished_no_channel or not existing_channel
        )

        return replay, _has_active_channel, existing_channel

    async def callback(self, ctx: discord.Interaction):
        """The callback that handles the button click.
        The new equivalent to the $play command.

        :param ctx: the Interaction context.
        """
        # checks
        replay, _has_active_channel, existing_channel = await self._get_checks(ctx)

        if _has_active_channel:
            return await ctx.response.send_message(
                f"You already have a channel for {self.game_config.game}.",
                ephemeral=True,
            )

        # Channel details
        channel_name = self._get_channel_name(ctx, replay)
        meta_role_id = await MetaRoleSelect.ask_for_meta_role(ctx, self.game_config)
        if type(meta_role_id) is bool and meta_role_id is False:
            return

        permissions = get_channel_permissions(ctx, self.game_config, meta_role_id)

        # Try creating the channel on discord
        channel = await create_channel_in_guild(
            ctx, self.game_config, channel_name, permissions
        )
        if channel is None:
            return

        # Create the channel on the DB
        if existing_channel:
            await update_channel_id(existing_channel, channel.id)
        else:
            await create_channel_in_db(
                ctx, self.game_config, channel.id, finished=replay
            )

        # Send instructions
        instructions_msg = await channel.send(get_instructions(self.game_config))
        await channel.send(ctx.user.mention)
        await instructions_msg.pin()

        # Closing statement
        try:
            await ctx.response.send_message(
                content=f"Successfully created your channel: {channel.mention}, have fun!",
                ephemeral=True,
            )
        except discord.errors.InteractionResponded:
            await ctx.edit_original_response(
                content=f"Successfully created your channel: {channel.mention}, have fun!",
                view=None,
            )

    @classmethod
    async def gen_button_view(
        cls, client: discord.Bot, guild_id: int, order: list[str] = None
    ) -> discord.ui.View:
        """Class utility to generate a view containing all the GameButtons for a given Guild.

        :param client: the Bot client.
        :param guild_id: the Guild ID to generate the button view for.
        :return: a Discord View with all the appropriate buttons.
        """
        game_configs: list[GameConfig] = await get_playable_games(guild_id)

        # HACK sorting for rigs
        if order is not None:
            if set([gc.game.name for gc in game_configs]) != set(order):
                return None
            else:
                new_game_configs = []
                for name in order:
                    for gc in game_configs:
                        if gc.game.name == name:
                            new_game_configs.append(gc)
                            break
                game_configs = new_game_configs

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
    """A View with a Select populated by Meta Roles to choose from."""

    class _Select(discord.ui.Select):
        """The actual Select UI component."""

        async def callback(self, ctx: discord.Interaction):
            """The callback that handles the selection.

            :param ctx: the Interaction context.
            """
            meta_role_id = self.values[0]
            if meta_role_id == "None":
                meta_role_id = None
            await self.view.picked_option(meta_role_id)

    def __init__(self, *items, meta_roles: list[MetaRoleConfig], timeout=20):
        """A View with a Select populated by Meta Roles to choose from.
        Please attach an `interaction` member upon creation.

        :param meta_roles: the MetaRoleConfigs to populate the View from.
        """
        super().__init__(*items, timeout=timeout)
        options = options = [discord.SelectOption(label="None", value="None")] + [
            discord.SelectOption(label=meta_role.name, value=meta_role.role_id)
            for meta_role in meta_roles
        ]
        self.add_item(self._Select(options=options))
        self.value = False

    async def on_timeout(self) -> None:
        """Timeout handler. Disables self."""
        self.children[0].disabled = True
        await self.interaction.edit_original_response(view=self)
        self.value = False

    async def picked_option(self, meta_role_id: int):
        """Selection handler. Disables self and sets value.

        :param meta_role_id: the selected MetaRoleConfig's `role_id`.
        """
        self.value = meta_role_id
        self.children[0].disabled = True
        await self.interaction.edit_original_response(view=self)
        self.stop()

    @classmethod
    async def ask_for_meta_role(
        cls,
        ctx: discord.Interaction,
        game_config: GameConfig,
    ):
        """Quick utility to spawn a MetaRoleSelect dialogue and return its value, if any.

        :param ctx: the Interaction context in which to spawn the dialogue.
        :param game_config: the GameConfig for which to launch the dialogue.
        """
        meta_roles = await get_meta_roles(game_config)
        if len(meta_roles) > 0:
            select = cls(meta_roles=meta_roles)
            select.interaction = await ctx.response.send_message(
                "Would you like to lock the channel behind a Meta-Role? If not or unsure, select `None`.",
                view=select,
                ephemeral=True,
            )
            await select.wait()
            return select.value
        else:
            return None
