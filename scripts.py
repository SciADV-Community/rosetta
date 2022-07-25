#!/usr/bin/env python
"""Commandline utility to inetteract with the bot."""
import os
import runpy
import subprocess
from pathlib import Path

import click
import django


@click.group()
def scripts():
    """Scripts group wrappper."""
    pass


@scripts.command()
@click.option(
    "--prefix", "-p", prompt="Prefix to use for bot commands", type=str, default="$"
)
@click.option(
    "--description", "-d", prompt="The bot's description text", type=str, default=""
)
@click.option("--token", "-t", prompt="The bot's access token", type=str)
def config(prefix, description, token):
    """Initialize the bot's configuration."""
    root_dir = Path(__file__).parent

    # Save into .env file
    dotenv = root_dir / ".env"
    with dotenv.open(mode="w") as f:
        f.writelines(
            [
                f"ROSETTA_PREFIX={prefix}\n",
                f"ROSETTA_TOKEN={token}\n",
                f"ROSETTA_DESCRIPTION={description}\n",
            ]
        )

    click.secho("Config initalized successfully.", fg="green")


@scripts.command()
def test():
    """Run tests."""
    subprocess.run("pytest")


@scripts.command()
def start():
    """Run the bot."""
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "genki.settings")
    django.setup()
    runpy.run_module("rosetta.main", run_name="__main__")


if __name__ == "__main__":
    scripts()
