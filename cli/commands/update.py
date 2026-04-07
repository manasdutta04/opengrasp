from __future__ import annotations

import subprocess
import sys
from importlib import metadata

import typer

from cli.ui import console, panel


def _version() -> str:
    try:
        return metadata.version("openapply")
    except Exception:
        return "unknown"


def command() -> None:
    """Update OpenApply to the latest version (pip)."""
    before = _version()
    console.print(panel("Update", f"Current version: {before}\nRunning: python -m pip install -U openapply"))

    try:
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "-U", "openapply"],
            check=True,
        )
    except Exception as exc:
        console.print(panel("Update failed", f"[bad]{exc}[/bad]\nTry manually:\n  python -m pip install -U openapply"))
        raise typer.Exit(code=1) from exc

    after = _version()
    console.print(panel("Updated", f"Installed version: {after}"))

