import click


@click.command()
@click.argument("channel_id", type=int)
@click.pass_context
async def delete(context, channel_id):
    """Command to delete a specific channel"""
    # discord_context = context.obj["discord_context"]
    # guild_id = discord_context.guild.id
    # channel = Channel.get(guild_id=guild_id, id=channel_id)
    # if channel:
    #     channel.delete()

    # channel = get(discord_context.guild.channels, id=channel_id)
    # if channel:
    #     await channel.delete(reason=f"Admin command by: {discord_context.author.name}")

    # await discord_context.send("Successfully deleted channel.")
    pass


__all__ = [
    'delete'
]
