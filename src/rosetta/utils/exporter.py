import docker
import os
from rosetta.config import TOKEN


client = docker.from_env()


def export_channel(channel_id: str):
    client.containers.run(
        'tyrrrz/discordchatexporter:stable',
        f'export -b -t {TOKEN} -c {channel_id} -o {channel_id}.xml',
        auto_remove=True,
        volumes={
            f'{os.getcwd()}/archives': {
                'bind': '/app/out', 'mode': 'rw'
            }
        }
    )


__all__ = ['export_channel']
