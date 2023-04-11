import discord


class ConfirmView(discord.ui.View):
    """A view that has a confirmation prompt"""

    @discord.ui.button(label="Yes", style=discord.ButtonStyle.primary, row=0)
    async def confirm_callback(
        self, button: discord.ui.Button, ctx: discord.Interaction
    ):
        """The callback for the Yes button.

        :param button: the Yes Button itself.
        :param ctx: the Interaction context
        """
        await self.picked_option(True)

    @discord.ui.button(label="No", style=discord.ButtonStyle.secondary, row=0)
    async def decline_callback(
        self, button: discord.ui.Button, ctx: discord.Interaction
    ):
        """The callback for the No button.

        :param button: the No Button itself.
        :param ctx: the Interaction context
        """
        await self.picked_option(False)

    async def on_timeout(self) -> None:
        """Timeout handler. Disables self."""
        for button in self.children:
            button.disabled = True
        await self.interaction.edit_original_response(view=self)
        self.value = None

    async def picked_option(self, answer: bool):
        """Handler for picking an option. Disables self and returns the selected value.

        :param answer: the user's answer to the prompt.
        """
        self.value = answer
        for button in self.children:
            button.disabled = True
        await self.interaction.edit_original_response(view=self)
        self.stop()
