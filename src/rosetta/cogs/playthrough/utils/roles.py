from asgiref.sync import sync_to_async
from discord import ApplicationContext, Interaction, PermissionOverwrite
from discord.ext.commands import Context
from discord.utils import get

from playthrough.models import GameConfig, MetaRoleConfig

from rosetta.cogs.playthrough.utils.discord import get_game_completion_role
from rosetta.utils.role_expr import MetaRoleEvaluator


async def grant_completion_role(context: "Context", game_config: "GameConfig"):
    """Grant the message author the completion role for a certain game.

    :param context: The Discord Context.
    :param game_config: The game to get the completion role for."""
    completion_role = get_game_completion_role(context, game_config)
    await context.user.add_roles(completion_role)


async def remove_completion_role(context: "Context", game_config: "GameConfig"):
    """Removes the completion role for a certain game from the message author.

    :param context: The Discord Context.
    :param game_config: The game to get the completion role for."""
    completion_role = get_game_completion_role(context, game_config)
    await context.user.remove_roles(completion_role)


@sync_to_async
def get_meta_roles_to_grant(
    ctx: ApplicationContext, game_config: GameConfig
) -> list[MetaRoleConfig]:
    """Get which MetaRoles to grant the user, given that they just finished a certain game.

    :param context: The Discord Context
    :param game_config: The Game the user just finished.
    :return: The list of MetaRoles to add."""
    related_meta_roles: list[MetaRoleConfig] = game_config.meta_roles.all()
    meta_roles_to_add = []
    user_role_ids = set([str(role.id) for role in ctx.user.roles])
    user_role_ids.add(game_config.completion_role_id)

    for meta_role in related_meta_roles:
        related_games: list[GameConfig] = meta_role.games.all()
        related_roles = [game.completion_role_id for game in related_games]
        evaluator_input = {
            role_id: role_id in user_role_ids for role_id in related_roles
        }
        evaluator = MetaRoleEvaluator(evaluator_input)
        result = evaluator.evaluate(meta_role.expression)
        if result:
            meta_roles_to_add.append(meta_role)

    return meta_roles_to_add


async def grant_meta_roles(ctx: ApplicationContext, game_config: GameConfig):
    """Add meta roles the user is qualified for after they finished a certain game.

    :param ctx: The Discord Context
    :param game_config: The Game the user just finished."""
    meta_roles_to_add: list[MetaRoleConfig] = await get_meta_roles_to_grant(
        ctx, game_config
    )
    roles_to_add = []
    for meta_role in meta_roles_to_add:
        role_in_discord = get(ctx.guild.roles, id=int(meta_role.role_id))
        roles_to_add.append(role_in_discord)
    await ctx.user.add_roles(*roles_to_add)


def get_channel_permissions(
    ctx: Interaction, game_config: GameConfig, meta_role_id=None
) -> dict[object, PermissionOverwrite]:
    """Get the permissions to apply to a newly created channel.

    :param ctx: the Interaction context.
    :param game_config: the GameConfig for which the channel is being created.
    :param meta_role_id: the ID of the "Meta Role" to lock the channel behind.
    :return: a dictionary of PermissionOverwrites.
    """
    completion_role = get_game_completion_role(ctx, game_config)

    permissions = {
        ctx.guild.me: PermissionOverwrite(
            read_messages=True,
            read_message_history=True,
            manage_messages=True,
            send_messages=True,
        ),
        ctx.guild.default_role: PermissionOverwrite(
            read_messages=False,
            read_message_history=False,
        ),
        ctx.user: PermissionOverwrite(
            read_messages=True,
            read_message_history=True,
            send_messages=True,
            manage_messages=True,
            manage_channels=True,
            manage_permissions=True,
        ),
    }

    role_perms = PermissionOverwrite(
        read_messages=True,
        read_message_history=True,
    )

    if meta_role_id is not None:
        meta_role = get(ctx.guild.roles, id=int(meta_role_id))
        permissions[meta_role] = role_perms
    else:
        permissions[completion_role] = role_perms

    return permissions
