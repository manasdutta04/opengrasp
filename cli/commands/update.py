from __future__ import annotations

import subprocess
import sys
from importlib import metadata

import typer

from cli.ui import console, panel


def _version() -> str:
    try:
        return metadata.version("opengrasp")
    except Exception:
        return "unknown"


def _pip_update_cmd() -> list[str]:
    return [sys.executable, "-m", "pip", "install", "-U", "opengrasp"]


def _is_windows_exe_lock(exc: Exception) -> bool:
    text = str(exc).lower()
    return sys.platform.startswith("win") and "winerror 32" in text and "opengrasp.exe" in text


def _schedule_windows_update() -> None:
    # Run pip in a detached cmd after a short delay so this process can exit and release opengrasp.exe.
    delayed_cmd = f"ping 127.0.0.1 -n 3 >nul && {subprocess.list2cmdline(_pip_update_cmd())}"
    subprocess.Popen(
        ["cmd", "/c", delayed_cmd],
        creationflags=getattr(subprocess, "CREATE_NEW_CONSOLE", 0),
    )


def command() -> None:
    """Update OpenGrasp to the latest version (pip)."""
    before = _version()
    console.print(panel("Update", f"Current version: {before}\nRunning: python -m pip install -U opengrasp"))

    try:
        subprocess.run(_pip_update_cmd(), check=True)
    except Exception as exc:
        if _is_windows_exe_lock(exc):
            try:
                _schedule_windows_update()
                console.print(
                    panel(
                        "Update scheduled",
                        "Windows is locking opengrasp.exe while this command is running.\n"
                        "A separate updater window was started and will continue after this command exits.\n"
                        f"If needed, run manually:\n  {sys.executable} -m pip install -U opengrasp",
                    )
                )
                raise typer.Exit(code=0) from exc
            except Exception:
                pass
        console.print(
            panel(
                "Update failed",
                f"[bad]{exc}[/bad]\nTry manually:\n  {sys.executable} -m pip install -U opengrasp",
            )
        )
        raise typer.Exit(code=1) from exc

    after = _version()
    console.print(panel("Updated", f"Installed version: {after}"))

