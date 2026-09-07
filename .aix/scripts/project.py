#!/usr/bin/env python3
"""Leaf: locate the AIX project that a command acts on."""
from pathlib import Path


def find_project(start: Path):
    """Nearest folder at or above `start` holding .aix/config.yaml: that is the project aix operates on."""
    for d in [start, *start.parents]:
        if (d / ".aix" / "config.yaml").exists() or (d / "framework.yaml").exists():  # 2.0 marker, or a 1.x project to migrate
            return d
    return None
