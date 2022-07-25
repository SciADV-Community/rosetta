import discord


class ConfirmView(discord.ui.View):
    async def on_timeout(self) -> None:
        for button in self.children:
            button.disabled = True
        await self.interaction.edit_original_message(view=self)
        self.value = None

    async def picked_option(self, answer: bool):
        self.value = answer
        for button in self.children:
            button.disabled = True
        await self.interaction.edit_original_message(view=self)
        self.stop()

    @discord.ui.button(label="Yes", style=discord.ButtonStyle.primary, row=0)
    async def confirm_callback(
        self, button: discord.ui.Button, interaction: discord.Interaction
    ):
        await self.picked_option(True)

    @discord.ui.button(label="No", style=discord.ButtonStyle.secondary, row=0)
    async def decline_callback(
        self, button: discord.ui.Button, interaction: discord.Interaction
    ):
        await self.picked_option(False)
