import os
from pathlib import Path

import docker

from rosetta.config import ARCHIVE_ROOT, TOKEN

client = docker.from_env()


def export_channel(channel_id: str) -> Path:
    """Export a certain channel by its id.
    :param channel_id: The ID of the channel to export.
    :return: The `pathlib.Path` of the archive."""
    client.containers.run(
        "tyrrrz/discordchatexporter:stable",
        f"export -c {channel_id} -o /app/out/archives/{channel_id}.html",
        auto_remove=True,
        volumes={"rosetta_archives": {"bind": "/app/out/archives", "mode": "rw"}},
        user=f"{os.getuid()}:{os.getgid()}",
        environment={"DISCORD_TOKEN": TOKEN, "DISCORD_TOKEN_BOT": True},
        stdout=True,
    )
    return ARCHIVE_ROOT / f"{channel_id}.html"


__all__ = ["export_channel"]
