from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from memory.db import DEFAULT_SCORING_WEIGHTS, Evaluation, Job, ScoringWeight

from .ollama_client import OllamaClient, OllamaClientError


SCORE_KEYS: tuple[str, ...] = (
    "role_match",
    "skills_alignment",
    "seniority_fit",
    "compensation",
    "geographic",
    "company_stage",
    "product_market_fit",
    "growth_trajectory",
    "interview_likelihood",
    "timeline",
)


@dataclass(slots=True)
class EvaluationResult:
    job_id: int | None
    evaluation_id: int | None
    scores: dict[str, float]
    weighted_total: float
    grade: str
    summary: str
    top_strengths: list[str]
    key_gaps: list[str]
    recommendation: str
    report_path: Path
    evaluated_at: datetime
    model_used: str


class JobEvaluator:
    """Evaluate job descriptions against CV content using the 10-dimension framework."""

    def __init__(
        self,
        session_factory: sessionmaker[Session],
        ollama_client: OllamaClient,
        project_root: str | Path = ".",
        prompt_path: str | Path = "agent/prompts/evaluate.md",
    ) -> None:
        self._session_factory = session_factory
        self._ollama_client = ollama_client
        self._project_root = Path(project_root)
        self._prompt_path = Path(prompt_path)

    async def evaluate_job(self, job_id: int, cv_content: str) -> EvaluationResult:
        """Evaluate and persist results for a job already stored in the DB."""
        with self._session_factory() as session:
            job = session.get(Job, job_id)
            if job is None:
                raise ValueError(f"Job with id={job_id} was not found.")

            jd_content = (job.jd_extracted or job.jd_raw or "").strip()
            if not jd_content:
                raise ValueError("Job description is empty. Scrape or import JD before evaluation.")

            weights = self._load_scoring_weights(session)
            raw_payload = await self._evaluate_with_llm(cv_content=cv_content, jd_content=jd_content)
            result = self._build_result(
                payload=raw_payload,
                weights=weights,
                company=job.company,
                role=job.role,
                model_used=self._model_used_label(),
                job_id=job.id,
            )

            report_text = self._render_markdown_report(
                result=result,
                weights=weights,
                company=job.company,
                role=job.role,
                url=job.url,
            )
            self._write_report(result.report_path, report_text)

            self._persist_evaluation(session=session, job=job, result=result)
            return result

    async def evaluate_text(
        self,
        cv_content: str,
        jd_content: str,
        company: str | None = None,
        role: str | None = None,
        url: str | None = None,
    ) -> EvaluationResult:
        """Evaluate a JD text blob and save a markdown report without DB persistence."""
        with self._session_factory() as session:
            weights = self._load_scoring_weights(session)

        raw_payload = await self._evaluate_with_llm(cv_content=cv_content, jd_content=jd_content)
        result = self._build_result(
            payload=raw_payload,
            weights=weights,
            company=company,
            role=role,
            model_used=self._model_used_label(),
            job_id=None,
        )

        report_text = self._render_markdown_report(
            result=result,
            weights=weights,
            company=company,
            role=role,
            url=url,
        )
        self._write_report(result.report_path, report_text)
        return result

    async def _evaluate_with_llm(self, cv_content: str, jd_content: str) -> dict[str, Any]:
        prompt_template = self._load_prompt_template()
        prompt_body = prompt_template.format(cv_content=cv_content, jd_content=jd_content)

        system_prompt = (
            "You are Open Apply's job-fit evaluator. "
            "Follow instructions exactly and return only valid JSON."
        )

        try:
            payload = await self._ollama_client.complete_json(system_prompt=system_prompt, user_prompt=prompt_body)
        except OllamaClientError:
            raise
        except Exception as exc:
            raise OllamaClientError(f"Evaluation call failed: {exc}") from exc

        return payload

    def _load_prompt_template(self) -> str:
        prompt_file = self._project_root / self._prompt_path
        if not prompt_file.exists():
            raise FileNotFoundError(f"Missing prompt file: {prompt_file}")
        return prompt_file.read_text(encoding="utf-8")

    def _load_scoring_weights(self, session: Session) -> dict[str, float]:
        rows = session.scalars(select(ScoringWeight)).all()
        db_weights = {row.dimension: float(row.weight) for row in rows if row.dimension in SCORE_KEYS}

        merged_weights = {**DEFAULT_SCORING_WEIGHTS, **db_weights}
        total_weight = sum(merged_weights.values())
        if total_weight <= 0:
            return dict(DEFAULT_SCORING_WEIGHTS)

        return {key: value / total_weight for key, value in merged_weights.items()}

    def _build_result(
        self,
        payload: dict[str, Any],
        weights: dict[str, float],
        company: str | None,
        role: str | None,
        model_used: str,
        job_id: int | None,
    ) -> EvaluationResult:
        scores = self._normalize_scores(payload)
        weighted_total = self._calculate_weighted_total(scores=scores, weights=weights)

        gate_failed = scores["role_match"] < 2.0 or scores["skills_alignment"] < 2.0
        if gate_failed:
            weighted_total = min(weighted_total, 2.5)

        weighted_total = round(weighted_total, 2)
        grade = self._grade_from_score(weighted_total)

        summary = str(payload.get("summary", "")).strip()
        if not summary:
            summary = "No model summary was provided."

        top_strengths = self._safe_string_list(payload.get("top_strengths"), limit=3)
        key_gaps = self._safe_string_list(payload.get("key_gaps"), limit=3)

        recommendation = str(payload.get("recommendation", "maybe")).strip().lower()
        if recommendation not in {"apply", "skip", "maybe"}:
            recommendation = "maybe"

        evaluated_at = datetime.now(timezone.utc)
        report_path = self._build_report_path(
            company=company,
            role=role,
            evaluated_at=evaluated_at,
        )

        return EvaluationResult(
            job_id=job_id,
            evaluation_id=None,
            scores=scores,
            weighted_total=weighted_total,
            grade=grade,
            summary=summary,
            top_strengths=top_strengths,
            key_gaps=key_gaps,
            recommendation=recommendation,
            report_path=report_path,
            evaluated_at=evaluated_at,
            model_used=model_used,
        )

    def _normalize_scores(self, payload: dict[str, Any]) -> dict[str, float]:
        raw_scores = payload.get("scores")
        if not isinstance(raw_scores, dict):
            raise ValueError("Model response missing 'scores' object.")

        normalized: dict[str, float] = {}
        for key in SCORE_KEYS:
            value = raw_scores.get(key)
            if not isinstance(value, (int, float)):
                raise ValueError(f"Model response missing numeric score for '{key}'.")

            clamped = max(1.0, min(5.0, float(value)))
            normalized[key] = round(clamped, 1)

        return normalized

    @staticmethod
    def _calculate_weighted_total(scores: dict[str, float], weights: dict[str, float]) -> float:
        return sum(scores[key] * weights[key] for key in SCORE_KEYS)

    @staticmethod
    def _grade_from_score(score: float) -> str:
        if score >= 4.5:
            return "A"
        if score >= 4.0:
            return "B"
        if score >= 3.0:
            return "C"
        if score >= 2.0:
            return "D"
        return "F"

    @staticmethod
    def _safe_string_list(value: Any, limit: int = 3) -> list[str]:
        if not isinstance(value, list):
            return []

        cleaned: list[str] = []
        for item in value:
            if isinstance(item, str) and item.strip():
                cleaned.append(item.strip())
            if len(cleaned) >= limit:
                break

        return cleaned

    def _build_report_path(self, company: str | None, role: str | None, evaluated_at: datetime) -> Path:
        company_slug = self._slugify(company or "unknown-company")
        role_slug = self._slugify(role or "unknown-role")
        timestamp = evaluated_at.strftime("%Y%m%d-%H%M%S")

        reports_dir = self._project_root / "reports"
        reports_dir.mkdir(parents=True, exist_ok=True)

        return reports_dir / f"{company_slug}-{role_slug}-{timestamp}.md"

    @staticmethod
    def _slugify(value: str) -> str:
        lowered = value.lower()
        normalized = re.sub(r"[^a-z0-9]+", "-", lowered).strip("-")
        return normalized or "na"

    @staticmethod
    def _write_report(path: Path, content: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def _persist_evaluation(self, session: Session, job: Job, result: EvaluationResult) -> None:
        notes_payload = {
            "summary": result.summary,
            "top_strengths": result.top_strengths,
            "key_gaps": result.key_gaps,
            "recommendation": result.recommendation,
        }

        evaluation = Evaluation(
            job_id=job.id,
            score_total=result.weighted_total,
            grade=result.grade,
            score_role_match=result.scores["role_match"],
            score_skills=result.scores["skills_alignment"],
            score_seniority=result.scores["seniority_fit"],
            score_compensation=result.scores["compensation"],
            score_geographic=result.scores["geographic"],
            score_company_stage=result.scores["company_stage"],
            score_pmf=result.scores["product_market_fit"],
            score_growth=result.scores["growth_trajectory"],
            score_interview_likelihood=result.scores["interview_likelihood"],
            score_timeline=result.scores["timeline"],
            report_path=result.report_path.as_posix(),
            evaluated_at=result.evaluated_at,
            model_used=result.model_used,
            notes=json.dumps(notes_payload, ensure_ascii=True),
        )

        job.status = "evaluated"
        session.add(evaluation)
        session.add(job)
        session.commit()
        session.refresh(evaluation)
        result.evaluation_id = evaluation.id

    def _render_markdown_report(
        self,
        result: EvaluationResult,
        weights: dict[str, float],
        company: str | None,
        role: str | None,
        url: str | None,
    ) -> str:
        lines: list[str] = []
        lines.append("# Open Apply Evaluation Report")
        lines.append("")
        lines.append(f"- Evaluated At: {result.evaluated_at.isoformat()}")
        lines.append(f"- Company: {company or 'Unknown'}")
        lines.append(f"- Role: {role or 'Unknown'}")
        lines.append(f"- URL: {url or 'N/A'}")
        lines.append(f"- Model Used: {result.model_used}")
        lines.append("")
        lines.append("## Overall Verdict")
        lines.append("")
        lines.append(f"- Total Score: {result.weighted_total:.2f}/5.00")
        lines.append(f"- Grade: {result.grade}")
        lines.append(f"- Recommendation: {result.recommendation}")
        lines.append(f"- Summary: {result.summary}")
        lines.append("")
        lines.append("## Dimension Scores")
        lines.append("")
        lines.append("| Dimension | Score | Weight | Weighted Contribution |")
        lines.append("|-----------|-------|--------|-----------------------|")

        for key in SCORE_KEYS:
            score = result.scores[key]
            weight = weights[key]
            contribution = score * weight
            lines.append(
                f"| {key} | {score:.1f} | {weight:.2f} | {contribution:.2f} |"
            )

        lines.append("")
        lines.append("## Top Strengths")
        lines.append("")
        if result.top_strengths:
            for item in result.top_strengths:
                lines.append(f"- {item}")
        else:
            lines.append("- None provided")

        lines.append("")
        lines.append("## Key Gaps")
        lines.append("")
        if result.key_gaps:
            for item in result.key_gaps:
                lines.append(f"- {item}")
        else:
            lines.append("- None provided")

        lines.append("")
        lines.append("## Notes")
        lines.append("")
        lines.append("- Gate Rule: Final score is capped at 2.5 if role_match < 2.0 or skills_alignment < 2.0.")
        lines.append("- Human In The Loop: This report is advisory. Human review is required before apply decisions.")

        return "\n".join(lines).strip() + "\n"

    def _model_used_label(self) -> str:
        return self._ollama_client.selected_model()
