"""Configuration bindings for the bot."""
import os

PREFIX = os.getenv("BOT_PREFIX", "$")
DESCRIPTION = os.getenv("BOT_DESCRIPTION", "")
TOKEN = os.getenv("BOT_TOKEN")

INSTALLED_MODULES = [
    'modules.dummy',
    'modules.admin',
    'modules.playthrough',
]
