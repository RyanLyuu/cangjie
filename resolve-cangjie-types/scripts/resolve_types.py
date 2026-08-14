#!/usr/bin/env python3
"""Portable entry point for the self-contained enhanced type resolver."""

import sys
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SKILL_ROOT))

from type_resolution.cli import main


if __name__ == "__main__":
    raise SystemExit(main())
