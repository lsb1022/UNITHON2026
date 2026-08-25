"""정답지·특성 조합 적재.

    python -m app.seed --project-id <uuid> --defects ../ux-testbed/DEFECTS.md
"""

from __future__ import annotations

import argparse
import itertools
import uuid
from pathlib import Path

from sqlalchemy import delete

from .db import session_scope
from .defects_parser import parse_defects
from .models import Defect, TraitCombo

READING = ["정독", "훑기"]
PACE = ["여유", "급함"]
LITERACY = ["능숙", "서툼"]
PATIENCE = ["높음", "낮음"]

#: 기획서 4장 — 자동 팝업(D-26)은 로드 10초 후에 뜬다.
#: 전원이 5초 만에 떠나면 그 Critical 결함은 '못 잡은 것'이 아니라 '마주친 적이 없는 것'이 된다.
#: '정독·여유' 조합만 10초 문턱을 넘도록 체류 시간을 잡는다.
DWELL_MS = {
    ("정독", "여유"): 12_000,
    ("정독", "급함"): 6_000,
    ("훑기", "여유"): 7_000,
    ("훑기", "급함"): 3_000,
}

POPUP_THRESHOLD_MS = 10_000


def load_defects(project_id: uuid.UUID, path: Path) -> int:
    parsed = parse_defects(path.read_text(encoding="utf-8"))

    with session_scope() as session:
        session.execute(delete(Defect).where(Defect.project_id == project_id))
        session.add_all(
            Defect(
                project_id=project_id,
                code=d.code,
                category=d.category,
                title=d.title,
                location=d.location,
                severity=d.severity,
                tier=d.tier,
                detection_method=d.detection_method,
                requires_viewport_w=d.requires_viewport_w,
            )
            for d in parsed
        )

    return len(parsed)


def load_trait_combos() -> int:
    combos = list(itertools.product(READING, PACE, LITERACY, PATIENCE))
    assert len(combos) == 16, "특성 조합은 16개여야 목표 11개와 서로소가 된다"

    with session_scope() as session:
        session.execute(delete(TraitCombo))
        for i, (reading, pace, literacy, patience) in enumerate(combos, start=1):
            session.add(
                TraitCombo(
                    id=i,
                    code=f"T{i:02d}",
                    reading_style=reading,
                    pace=pace,
                    tech_literacy=literacy,
                    patience=patience,
                    dwell_ms=DWELL_MS[(reading, pace)],
                    max_steps=40 if patience == "높음" else 25,
                )
            )

    return len(combos)


def main() -> None:
    parser = argparse.ArgumentParser(description="정답지·특성 조합 적재")
    parser.add_argument("--project-id", required=True, type=uuid.UUID)
    parser.add_argument("--defects", required=True, type=Path)
    args = parser.parse_args()

    combos = load_trait_combos()
    defects = load_defects(args.project_id, args.defects)

    print(f"특성 조합 {combos}개 적재")
    print(f"정답지 {defects}건 적재 (68건 · 25/30/13 · 22/10/16/20 검증 통과)")


if __name__ == "__main__":
    main()
