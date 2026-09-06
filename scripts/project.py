#!/usr/bin/env python3
"""Leaf: locate the AIX project that a command acts on."""
from pathlib import Path


def find_project(start: Path):
    """Nearest folder at or above `start` holding framework.yaml: that is the project aix operates on."""
    for d in [start, *start.parents]:
        if (d / "framework.yaml").exists():
            return d
    return None
