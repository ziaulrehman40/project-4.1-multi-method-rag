#!/usr/bin/env python
import os
import sys
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR / "src"))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")


if __name__ == "__main__":
    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)

