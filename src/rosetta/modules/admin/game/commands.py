import click


@click.command()
@click.argument("game", type=str)
@click.option("--alias", "-a", type=str, help="alias for the game")
@click.option(
    "--completion_role", "-c", type=int, help="role id of the completion role"
)
@click.option("--channel_suffix", "-s", type=str, help="suffix of playthrough channels")
@click.option(
    "--category", "-a", type=int, help="category id to put active channels in"
)
@click.pass_context
async def add(
    context,
    game,
    alias=None,
    completion_role=None,
    channel_suffix=None,
    category=None,
):
    """Command to add a game"""
    # discord_context = context.obj["discord_context"]
    # guild_obj = Guild.get(id=discord_context.guild.id)

    # async with discord_context.typing():
    #     if Game.get(name=game):
    #         await discord_context.send(f"{game} already exists.")
    #         return

    #     if not channel_suffix:
    #         channel_suffix = f"plays-{game.lower().strip()}"

    #     game_obj = Game.create(name=game, channel_suffix=channel_suffix)
    #     if alias:
    #         GameAlias.create(name=alias, game=game_obj)

    #     if completion_role:
    #         role = get(discord_context.guild.roles, id=role)
    #     else:
    #         role = await discord_context.guild.create_role(name=game)
    #     CompletionRole.create(
    #         id=role.id, guild=guild_obj, name=role.name, game=game_obj
    #     )

    #     if active_category:
    #         category = get(discord_context.guild.categories, id=active_category)
    #     else:
    #         category = await discord_context.guild.create_category(
    #             name=f"{game} Playthroughs"
    #         )
    #     Category.create(
    #         id=category.id, guild=guild_obj, name=category.name, game_id=game_obj.id,
    #     )

    #     if finished_category:
    #         category = get(discord_context.guild.categories, id=finished_category)
    #     else:
    #         category = await discord_context.guild.create_category(
    #             name=f"{game} Archived"
    #         )
    #     Category.create(
    #         id=category.id,
    #         guild=guild_obj,
    #         name=category.name,
    #         game_id=game_obj.id,
    #         archival=True,
    #     )

    #     await discord_context.send(f"Successfully added {game}!")
    pass


@click.command()
@click.argument("game", type=str)
@click.pass_context
async def remove(context, game):
    """Command to remove a game"""
    # discord_context = context.obj["discord_context"]
    # game_obj = Game.get_by_alias(game)
    # if not game_obj:
    #     await discord_context.send(f"Game {game} not found. Try again!")
    #     return

    # game_obj.delete()
    # await discord_context.send(f"Game {game} successfully removed!")
    pass


__all__ = [
    'add',
    'remove'
]
