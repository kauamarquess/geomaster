#!/usr/bin/env python3
"""Atalho:  python tools/geomaster.py validate | stats | merge"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from geomaster_tools.cli import main  # noqa: E402

raise SystemExit(main())
