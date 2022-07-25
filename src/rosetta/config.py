"""Configuration bindings for the bot."""
import os
from pathlib import Path

DESCRIPTION = os.getenv("ROSETTA_DESCRIPTION", "")
TOKEN = os.getenv("ROSETTA_TOKEN")

_ROSETTA_ROOT = os.getenv("ROSETTA_ROOT")
BASE_DIR = (
    Path(_ROSETTA_ROOT).resolve()
    if _ROSETTA_ROOT
    else Path(__file__).resolve().parents[2]
)
ARCHIVE_ROOT = BASE_DIR / "archives"
LOG_ROOT = BASE_DIR / "logs"
