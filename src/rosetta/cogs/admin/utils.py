import re
from typing import List, Tuple, Optional
from asgiref.sync import sync_to_async

from playthrough.models import MetaRoleConfig, GameConfig, Guild

from rosetta.utils.role_expr import MetaRoleEvaluator


def clean_expr(expr: str) -> str:
    """Clean the given Meta Role logic expression.

    :param expression: The Meta Role logic expression to clean.
    :return: The cleaned expression."""
    expr = re.sub(r"[<>@]", "", expr)
    expr = re.sub(r"&(\d+)", r"\1", expr)
    return expr


@sync_to_async
def get_meta_role(guild_id: int, name: str) -> Optional[MetaRoleConfig]:
    return MetaRoleConfig.objects.filter(name=name, guild_id=guild_id).first()


@sync_to_async
def get_all_meta_roles_per_guild() -> dict[str, list[str]]:
    ret = {}
    guilds = list(Guild.objects.prefetch_related("meta_roles").all())

    for guild in guilds:
        ret[int(guild.id)] = [meta_role.name for meta_role in guild.meta_roles]

    return ret


@sync_to_async
def get_existing_meta_role(name: str) -> Optional[MetaRoleConfig]:
    return MetaRoleConfig.objects.filter(name=name).first()


@sync_to_async
def create_meta_role_config(
    name: str,
    colour: str,
    logic: str,
    guild_id: str,
    role_id: str,
    game_configs: List[GameConfig],
):
    meta_role_config = MetaRoleConfig(
        name=name,
        colour=colour,
        expression=logic,
        guild_id=guild_id,
        role_id=role_id,
    )
    meta_role_config.save()
    meta_role_config.games.add(*game_configs)


@sync_to_async
def validate_expr(expr: str) -> Tuple[Optional[List[GameConfig]], Optional[str]]:
    """Check whether or not the given Meta Role logic expression is valid.

    :param context: The Discord Context.
    :param expression: The expression to check.
    :return: Boolean of whether or not it's a valid expression."""
    role_ids = re.findall(r"\d+", expr)
    game_configs = []
    unconfigured_games = []
    for _role_id in role_ids:
        game_config = GameConfig.objects.filter(completion_role_id=_role_id).first()
        if game_config is not None:
            game_configs.append(game_config)
        else:
            unconfigured_games.append(_role_id)
    if len(game_configs) != len(role_ids):
        err = "Could not find configured games for: "
        err += str(", ".join([f"<@&{_role_id}>" for _role_id in unconfigured_games]))
        return None, err
    evaluator = MetaRoleEvaluator({_role_id: False for _role_id in role_ids})
    try:
        evaluator.evaluate(expr)
        return game_configs, None
    except Exception:
        return None, (
            (
                "The provided expression is invalid. Only use logical operators "
                "and role IDs / pings"
            )
        )
