"""채점 — 기획서 4장 "탐색 중에는 결함 분석을 시키지 않는다".

실행이 완전히 끝난 뒤 별개로 돈다. 그래서 이 모듈은 run/journey/step 을 **읽기만** 한다.
쓰는 곳은 finding / finding_match / run_score 뿐이다.

재현율의 분모를 고르는 규칙:
    기획서 6장이 인정한 상한 — 뷰포트가 1280 고정이라 375px에서만 드러나는 3건은
    원리적으로 못 잡는다. 그것을 분모에 넣으면 '못 잡음'과 '잡을 수 없음'이 섞인다.
    분모를 두 개(전체 / 도달 가능) 다 남겨서 발표 때 어느 쪽인지 밝힐 수 있게 한다.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .models import Defect, Finding, FindingMatch, Project, Run, RunScore, SiteVariant


@dataclass
class ScoreResult:
    defects_total: int
    defects_reachable: int
    defects_found: int
    findings_total: int
    true_positives: int
    false_positives: int
    recall: Decimal | None
    precision: Decimal | None
    fp_rate: Decimal | None


def _ratio(numerator: int, denominator: int, places: str = "0.0001") -> Decimal | None:
    if denominator == 0:
        return None
    return (Decimal(numerator) / Decimal(denominator)).quantize(Decimal(places))


def compute(session: Session, run_id: uuid.UUID, scorer_version: str) -> ScoreResult:
    run = session.get(Run, run_id)
    if run is None:
        raise ValueError(f"run {run_id} 없음")

    variant = session.get(SiteVariant, run.site_variant_id)
    project = session.get(Project, variant.project_id)

    defects = list(session.scalars(select(Defect).where(Defect.project_id == project.id)))
    # 이 실행의 뷰포트로 도달 가능한 결함만 재현율의 '정직한' 분모다.
    reachable = [
        d for d in defects
        if d.requires_viewport_w is None or d.requires_viewport_w >= project.viewport_w
    ]

    matches = list(
        session.scalars(
            select(FindingMatch)
            .join(Finding, Finding.id == FindingMatch.finding_id)
            .where(Finding.run_id == run_id, Finding.scorer_version == scorer_version)
        )
    )

    findings_total = session.scalar(
        select(func.count(Finding.id)).where(
            Finding.run_id == run_id, Finding.scorer_version == scorer_version
        )
    ) or 0

    true_positives = sum(1 for m in matches if m.verdict == "true_positive")
    false_positives = sum(1 for m in matches if m.verdict == "false_positive")
    found_defects = {m.defect_id for m in matches if m.defect_id is not None}

    # clean 실행에서는 정답지가 없다. 기획서 5장: 여기서 나온 지적은 전부 오탐이다.
    if variant.is_control:
        recall = None
        false_positives = findings_total
        true_positives = 0
        found_defects = set()
    else:
        recall = _ratio(len(found_defects), len(reachable))

    precision = _ratio(true_positives, true_positives + false_positives)
    # 기획서 DEFECTS.md: FP rate = clean에서의 지적 수 / clean 페이지 수
    pages = session.scalar(
        select(func.count(func.distinct(Finding.screen_key))).where(Finding.run_id == run_id)
    ) or 0
    fp_rate = _ratio(false_positives, pages, "0.0001")

    return ScoreResult(
        defects_total=len(defects),
        defects_reachable=len(reachable),
        defects_found=len(found_defects),
        findings_total=findings_total,
        true_positives=true_positives,
        false_positives=false_positives,
        recall=recall,
        precision=precision,
        fp_rate=fp_rate,
    )


def persist(session: Session, run_id: uuid.UUID, scorer_version: str) -> RunScore:
    """발표에 올릴 수치를 채점기 버전과 함께 고정한다. 같은 버전으로 다시 매기면 덮어쓴다."""
    result = compute(session, run_id, scorer_version)

    score = session.scalar(
        select(RunScore).where(
            RunScore.run_id == run_id, RunScore.scorer_version == scorer_version
        )
    )
    if score is None:
        score = RunScore(run_id=run_id, scorer_version=scorer_version)
        session.add(score)

    score.defects_total = result.defects_reachable
    score.defects_found = result.defects_found
    score.findings_total = result.findings_total
    score.true_positives = result.true_positives
    score.false_positives = result.false_positives
    score.recall = result.recall
    score.precision = result.precision
    score.fp_rate = result.fp_rate

    return score
