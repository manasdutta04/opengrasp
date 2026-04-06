from __future__ import annotations

import typer
from rich.console import Console

from cli.commands import apply, setup

app = typer.Typer(
    help=(
        "Open Apply CLI.\n\n"
        "Examples:\n"
        "  openapply setup\n"
        "  openapply apply <url-or-jd-text>\n"
        "  openapply --help\n"
    ),
    no_args_is_help=True,
    rich_markup_mode="rich",
)

console = Console()


@app.callback()
def main() -> None:
    """Open Apply command registry."""
    return None


@app.command(
    "setup",
    help=(
        "Run first-time setup wizard.\n\n"
        "Example:\n"
        "  openapply setup"
    ),
)
def setup_command() -> None:
    setup.command()


@app.command(
    "apply",
    help=(
        "Evaluate and process one job URL or JD text.\n\n"
        "Examples:\n"
        "  openapply apply https://boards.greenhouse.io/company/jobs/123\n"
        "  openapply apply \"Senior Backend Engineer ...\""
    ),
)
def apply_command(target: str = typer.Argument(..., help="Job URL or raw JD text.")) -> None:
    apply.command(target)


if __name__ == "__main__":
    app()
