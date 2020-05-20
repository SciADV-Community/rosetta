#!/usr/bin/env python
"""Commandline utility to inetteract with the bot."""
import re
import subprocess
import runpy
from pathlib import Path
import click
import inquirer
import yaml


def stringify_list(values, process=None):
    """Change a python list into its string representation."""
    strings = [f'"{value}"' for value in values if value]
    if process:
        strings = [process(string) for string in strings]
    return f"[{', '.join(strings)}]"


@click.command()
@click.option(
    "--prefix", "-p", prompt="Prefix to use for bot commands", type=str, default="$"
)
@click.option(
    "--description", "-d", prompt="The bot's description text", type=str, default=""
)
@click.option("--token", "-t", prompt="The bot's access token", type=str)
@click.option("--admins", "-a", prompt="User IDs of Bot admins", type=str, default="")
def config(prefix, description, token, admins):
    """Initialize the bot's configuration."""
    root_dir = Path(__file__).parent

    # Admin parsing
    admins = ";".join(re.split(r", |,| ", admins))

    # Module prompt
    module_folder = root_dir / "src" / "rosetta" / "modules"
    all_modules = [
        file.stem
        for file in module_folder.glob("*.py")
        if not file.stem.startswith("__") and file.stem != "help"
    ]

    questions = [
        inquirer.Checkbox(
            "mods", message="Select the modules you want to load", choices=all_modules
        )
    ]
    answers = inquirer.prompt(questions)
    modules = ";".join([f"{module}" for module in answers["mods"]])

    questions = [
        inquirer.Checkbox(
            "startup_mods",
            message="Select the modules you want to load on startup",
            choices=answers["mods"],
        )
    ]
    answers = inquirer.prompt(questions)
    startup_modules = ";".join([f"{module}" for module in answers["startup_mods"]])

    # Save into .env file
    dotenv = root_dir / ".env"
    with dotenv.open(mode="w") as f:
        f.writelines(
            [
                f"BOT_PREFIX={prefix}\n",
                f"BOT_TOKEN={token}\n",
                f"BOT_DESCRIPTION={description}\n",
                f"BOT_ADMINS={admins}\n",
                f"BOT_MODULES={modules}\n",
                f"BOT_STARTUP_MODULES={startup_modules}\n",
                f"BOT_DB={database}\n",
            ]
        )

    click.secho("Config initalized successfully.", fg="green")


@click.command()
def test():
    """Run tests."""
    subprocess.run("pytest")


@click.command()
def start():
    """Run the bot."""
    runpy.run_module("rosetta.main", run_name="__main__")
