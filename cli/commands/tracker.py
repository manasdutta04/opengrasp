from __future__ import annotations

import msvcrt
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Literal

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from sqlalchemy import desc, select

from cli.commands import apply as apply_command
from memory.db import Application, Evaluation, Job, Outcome, build_session_factory, create_sqlite_engine, initialize_database

console = Console()

SortBy = Literal["score", "date", "company"]


@dataclass(slots=True)
class TrackerRow:
    job_id: int
    company: str
    role: str
    score: float | None
    grade: str | None
    status: str
    date: datetime
    report_path: str | None
    url: str


def _parse_date(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d")
    except ValueError as exc:
        raise typer.BadParameter("Dates must use YYYY-MM-DD format.") from exc


def _fetch_rows(
    grade: str | None,
    status: str | None,
    date_from: datetime | None,
    date_to: datetime | None,
    sort_by: SortBy,
) -> list[TrackerRow]:
    engine = create_sqlite_engine()
    initialize_database(engine)
    session_factory = build_session_factory(engine)

    with session_factory() as session:
        jobs = session.scalars(select(Job).order_by(desc(Job.scraped_at))).all()
        rows: list[TrackerRow] = []

        for job in jobs:
            eval_row = session.scalars(
                select(Evaluation).where(Evaluation.job_id == job.id).order_by(desc(Evaluation.id)).limit(1)
            ).first()

            app_row = session.scalars(
                select(Application).where(Application.job_id == job.id).order_by(desc(Application.id)).limit(1)
            ).first()

            effective_status = app_row.outcome if app_row is not None else job.status
            if status and effective_status.lower() != status.lower():
                continue

            score = eval_row.score_total if eval_row is not None else None
            grade_value = eval_row.grade if eval_row is not None else None
            if grade and (grade_value or "").upper() != grade.upper():
                continue

            date_value = job.scraped_at.replace(tzinfo=None) if job.scraped_at.tzinfo else job.scraped_at
            if date_from and date_value < date_from:
                continue
            if date_to and date_value > date_to.replace(hour=23, minute=59, second=59):
                continue

            rows.append(
                TrackerRow(
                    job_id=job.id,
                    company=job.company or "Unknown",
                    role=job.role or "Unknown",
                    score=score,
                    grade=grade_value,
                    status=effective_status,
                    date=date_value,
                    report_path=eval_row.report_path if eval_row is not None else None,
                    url=job.url,
                )
            )

    if sort_by == "score":
        rows.sort(key=lambda row: row.score if row.score is not None else -1.0, reverse=True)
    elif sort_by == "company":
        rows.sort(key=lambda row: row.company.lower())
    else:
        rows.sort(key=lambda row: row.date, reverse=True)

    return rows


def _render_table(rows: list[TrackerRow], selected_index: int) -> None:
    table = Table(title="Open Apply Tracker")
    table.add_column("Job ID", justify="right", style="cyan")
    table.add_column("Company", style="green")
    table.add_column("Role")
    table.add_column("Score", justify="right")
    table.add_column("Grade", justify="center")
    table.add_column("Status")
    table.add_column("Date")

    for idx, row in enumerate(rows):
        style = "reverse" if idx == selected_index else ""
        table.add_row(
            str(row.job_id),
            row.company,
            row.role,
            f"{row.score:.2f}" if row.score is not None else "-",
            row.grade or "-",
            row.status,
            row.date.strftime("%Y-%m-%d"),
            style=style,
        )

    console.clear()
    console.print(table)
    console.print(
        Panel.fit(
            "Use Up/Down arrows to navigate. Press E=open report, A=run apply flow, "
            "L=log outcome, Q=quit.",
            border_style="blue",
        )
    )


def _read_key() -> str:
    first = msvcrt.getwch()
    if first in ("\x00", "\xe0"):
        second = msvcrt.getwch()
        if second == "H":
            return "UP"
        if second == "P":
            return "DOWN"
        return "SPECIAL"
    return first


def _open_report(row: TrackerRow) -> None:
    if not row.report_path:
        console.print("[yellow]No report available for this job yet.[/yellow]")
        return

    path = Path(row.report_path)
    if not path.exists():
        console.print(f"[yellow]Report file not found:[/yellow] {path.as_posix()}")
        return

    content = path.read_text(encoding="utf-8")
    console.print(Panel(content, title=f"Report: {path.name}", border_style="magenta"))


def _run_apply_for_row(row: TrackerRow) -> None:
    if not row.url.startswith("http"):
        console.print("[yellow]Cannot run apply flow: selected row has no URL target.[/yellow]")
        return

    console.print(f"[bold]Running apply flow for:[/bold] {row.url}")
    apply_command.command(row.url)


def _log_outcome_for_row(row: TrackerRow) -> None:
    outcome = typer.prompt(
        "Outcome (interview/rejected/offer/ghosted)",
        default="interview",
    ).strip().lower()

    if outcome not in {"interview", "rejected", "offer", "ghosted"}:
        console.print("[red]Invalid outcome.[/red]")
        return

    notes = typer.prompt("Notes", default="").strip()

    engine = create_sqlite_engine()
    session_factory = build_session_factory(engine)

    with session_factory() as session:
        app_row = session.scalars(
            select(Application).where(Application.job_id == row.job_id).order_by(desc(Application.id)).limit(1)
        ).first()

        if app_row is None:
            app_row = Application(
                job_id=row.job_id,
                cv_id=None,
                auto_applied=False,
                human_reviewed=True,
                outcome=outcome,
            )
            session.add(app_row)
            session.flush()
        else:
            app_row.outcome = outcome
            session.add(app_row)

        outcome_row = Outcome(
            application_id=app_row.id,
            outcome_type=outcome,
            notes=notes or None,
        )
        session.add(outcome_row)

        job = session.get(Job, row.job_id)
        if job is not None:
            if outcome in {"interview", "offer", "rejected"}:
                job.status = outcome
            session.add(job)

        session.commit()

    console.print("[green]Outcome logged.[/green]")


def command(
    grade: str | None = typer.Option(None, "--grade", help="Filter by grade (A/B/C/D/F)."),
    status: str | None = typer.Option(None, "--status", help="Filter by status."),
    date_from: str | None = typer.Option(None, "--date-from", help="Start date YYYY-MM-DD."),
    date_to: str | None = typer.Option(None, "--date-to", help="End date YYYY-MM-DD."),
    sort_by: SortBy = typer.Option("date", "--sort-by", help="Sort by: score, date, company."),
) -> None:
    """Interactive tracker dashboard.

    Examples:
      openapply tracker
      openapply tracker --grade B --status applied --sort-by score
      openapply tracker --date-from 2026-01-01 --date-to 2026-04-30
    """
    parsed_from = _parse_date(date_from)
    parsed_to = _parse_date(date_to)

    rows = _fetch_rows(
        grade=grade,
        status=status,
        date_from=parsed_from,
        date_to=parsed_to,
        sort_by=sort_by,
    )

    if not rows:
        console.print("[yellow]No jobs match current filters.[/yellow]")
        return

    selected_index = 0

    while True:
        _render_table(rows, selected_index)
        key = _read_key()

        if key == "UP":
            selected_index = max(0, selected_index - 1)
            continue

        if key == "DOWN":
            selected_index = min(len(rows) - 1, selected_index + 1)
            continue

        if key.lower() == "q":
            console.print("Exiting tracker.")
            return

        current = rows[selected_index]

        if key.lower() == "e":
            _open_report(current)
            console.print("Press any key to continue...")
            _read_key()
            continue

        if key.lower() == "a":
            _run_apply_for_row(current)
            rows = _fetch_rows(
                grade=grade,
                status=status,
                date_from=parsed_from,
                date_to=parsed_to,
                sort_by=sort_by,
            )
            selected_index = min(selected_index, len(rows) - 1) if rows else 0
            if not rows:
                console.print("[yellow]No rows remain for current filters.[/yellow]")
                return
            continue

        if key.lower() == "l":
            _log_outcome_for_row(current)
            rows = _fetch_rows(
                grade=grade,
                status=status,
                date_from=parsed_from,
                date_to=parsed_to,
                sort_by=sort_by,
            )
            selected_index = min(selected_index, len(rows) - 1) if rows else 0
            if not rows:
                console.print("[yellow]No rows remain for current filters.[/yellow]")
                return
            continue
