"""Configuration bindings for the bot."""
import os
from pathlib import Path

PREFIX = os.getenv("BOT_PREFIX", "$")
DESCRIPTION = os.getenv("BOT_DESCRIPTION", "")
TOKEN = os.getenv("BOT_TOKEN")

INSTALLED_MODULES = [
    'modules.admin',
    'modules.playthrough',
]

BASE_DIR = Path(__file__).resolve().parents[2]

ARCHIVE_ROOT = BASE_DIR / 'archives'
