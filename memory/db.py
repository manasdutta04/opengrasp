from __future__ import annotations

from collections.abc import Generator
from datetime import datetime, timezone
from pathlib import Path
from typing import Final

from sqlalchemy import Boolean, DateTime, Enum, Float, ForeignKey, Integer, String, Text, create_engine, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, relationship, sessionmaker


JOB_STATUS_VALUES: Final[tuple[str, ...]] = (
    "new",
    "evaluated",
    "applied",
    "interview",
    "offer",
    "rejected",
    "skipped",
)

GRADE_VALUES: Final[tuple[str, ...]] = ("A", "B", "C", "D", "F")

APPLICATION_OUTCOME_VALUES: Final[tuple[str, ...]] = (
    "pending",
    "interview",
    "rejected",
    "offer",
    "ghosted",
)

OUTCOME_TYPE_VALUES: Final[tuple[str, ...]] = (
    "interview",
    "rejected",
    "offer",
    "ghosted",
)

PORTAL_TYPE_VALUES: Final[tuple[str, ...]] = (
    "greenhouse",
    "ashby",
    "lever",
    "linkedin",
    "custom",
)

DEFAULT_SCORING_WEIGHTS: Final[dict[str, float]] = {
    "role_match": 0.20,
    "skills_alignment": 0.20,
    "seniority_fit": 0.12,
    "compensation": 0.12,
    "geographic": 0.08,
    "company_stage": 0.08,
    "product_market_fit": 0.08,
    "growth_trajectory": 0.07,
    "interview_likelihood": 0.03,
    "timeline": 0.02,
}


class Base(DeclarativeBase):
    pass


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    url: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    company: Mapped[str | None] = mapped_column(Text, nullable=True)
    role: Mapped[str | None] = mapped_column(Text, nullable=True)
    jd_raw: Mapped[str | None] = mapped_column(Text, nullable=True)
    jd_extracted: Mapped[str | None] = mapped_column(Text, nullable=True)
    scraped_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    status: Mapped[str] = mapped_column(
        Enum(*JOB_STATUS_VALUES, name="job_status", native_enum=False, create_constraint=True),
        default="new",
        nullable=False,
    )

    evaluations: Mapped[list[Evaluation]] = relationship(back_populates="job", cascade="all, delete-orphan")
    cvs: Mapped[list[CV]] = relationship(back_populates="job", cascade="all, delete-orphan")
    applications: Mapped[list[Application]] = relationship(back_populates="job", cascade="all, delete-orphan")


class Evaluation(Base):
    __tablename__ = "evaluations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False)
    score_total: Mapped[float] = mapped_column(Float, nullable=False)
    grade: Mapped[str] = mapped_column(
        Enum(*GRADE_VALUES, name="grade_value", native_enum=False, create_constraint=True),
        nullable=False,
    )
    score_role_match: Mapped[float] = mapped_column(Float, nullable=False)
    score_skills: Mapped[float] = mapped_column(Float, nullable=False)
    score_seniority: Mapped[float] = mapped_column(Float, nullable=False)
    score_compensation: Mapped[float] = mapped_column(Float, nullable=False)
    score_geographic: Mapped[float] = mapped_column(Float, nullable=False)
    score_company_stage: Mapped[float] = mapped_column(Float, nullable=False)
    score_pmf: Mapped[float] = mapped_column(Float, nullable=False)
    score_growth: Mapped[float] = mapped_column(Float, nullable=False)
    score_interview_likelihood: Mapped[float] = mapped_column(Float, nullable=False)
    score_timeline: Mapped[float] = mapped_column(Float, nullable=False)
    report_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    evaluated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    model_used: Mapped[str | None] = mapped_column(String(255), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    job: Mapped[Job] = relationship(back_populates="evaluations")
    cvs: Mapped[list[CV]] = relationship(back_populates="evaluation")


class CV(Base):
    __tablename__ = "cvs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False)
    evaluation_id: Mapped[int | None] = mapped_column(ForeignKey("evaluations.id", ondelete="SET NULL"), nullable=True)
    cv_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    pdf_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    keywords_injected: Mapped[str | None] = mapped_column(Text, nullable=True)
    archetype_used: Mapped[str | None] = mapped_column(String(255), nullable=True)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    job: Mapped[Job] = relationship(back_populates="cvs")
    evaluation: Mapped[Evaluation | None] = relationship(back_populates="cvs")
    applications: Mapped[list[Application]] = relationship(back_populates="cv")


class Application(Base):
    __tablename__ = "applications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False)
    cv_id: Mapped[int | None] = mapped_column(ForeignKey("cvs.id", ondelete="SET NULL"), nullable=True)
    applied_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    auto_applied: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    human_reviewed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    response_received_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    outcome: Mapped[str] = mapped_column(
        Enum(*APPLICATION_OUTCOME_VALUES, name="application_outcome", native_enum=False, create_constraint=True),
        default="pending",
        nullable=False,
    )

    job: Mapped[Job] = relationship(back_populates="applications")
    cv: Mapped[CV | None] = relationship(back_populates="applications")
    outcomes: Mapped[list[Outcome]] = relationship(back_populates="application", cascade="all, delete-orphan")


class Outcome(Base):
    __tablename__ = "outcomes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    application_id: Mapped[int] = mapped_column(ForeignKey("applications.id", ondelete="CASCADE"), nullable=False)
    outcome_type: Mapped[str] = mapped_column(
        Enum(*OUTCOME_TYPE_VALUES, name="outcome_type", native_enum=False, create_constraint=True),
        nullable=False,
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    logged_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    application: Mapped[Application] = relationship(back_populates="outcomes")


class ScoringWeight(Base):
    __tablename__ = "scoring_weights"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    dimension: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    weight: Mapped[float] = mapped_column(Float, nullable=False)
    last_updated: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class Portal(Base):
    __tablename__ = "portals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    type: Mapped[str] = mapped_column(
        Enum(*PORTAL_TYPE_VALUES, name="portal_type", native_enum=False, create_constraint=True),
        nullable=False,
    )
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


def default_db_url(project_root: Path | None = None) -> str:
    root = project_root or Path.cwd()
    db_dir = root / "data"
    db_dir.mkdir(parents=True, exist_ok=True)
    return f"sqlite:///{(db_dir / 'openapply.db').as_posix()}"


def create_sqlite_engine(database_url: str | None = None) -> Engine:
    url = database_url or default_db_url()
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    return create_engine(url, future=True, connect_args=connect_args)


def build_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)


def initialize_database(engine: Engine) -> None:
    Base.metadata.create_all(bind=engine)
    session_factory = build_session_factory(engine)
    with session_factory() as session:
        _seed_default_scoring_weights(session)


def get_session(session_factory: sessionmaker[Session]) -> Generator[Session, None, None]:
    session = session_factory()
    try:
        yield session
    finally:
        session.close()


def _seed_default_scoring_weights(session: Session) -> None:
    existing_dimensions = set(session.scalars(select(ScoringWeight.dimension)).all())
    now = datetime.now(timezone.utc)

    created = False
    for dimension, weight in DEFAULT_SCORING_WEIGHTS.items():
        if dimension in existing_dimensions:
            continue
        session.add(
            ScoringWeight(
                dimension=dimension,
                weight=weight,
                last_updated=now,
            )
        )
        created = True

    if created:
        session.commit()
