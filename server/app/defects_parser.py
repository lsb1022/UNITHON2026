"""DEFECTS.md 파서 — DB 의존이 없다. 단독으로 검증할 수 있어야 한다.

정답지를 손으로 옮겨 적으면 오타 한 글자가 재현율의 분모를 바꾼다.
그래서 문서를 그대로 읽고, 기획서에 적힌 집계와 어긋나면 예외를 던진다.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

SEVERITY_MAP = {"Critical": "critical", "High": "high", "Medium": "medium"}

EXPECTED_TOTAL = 68
EXPECTED_SEVERITY = {"critical": 25, "high": 30, "medium": 13}
EXPECTED_TIER = {"static": 22, "render": 10, "interaction": 16, "semantic": 20}

TIER_HEADINGS = [
    ("static", "정적 분석만으로"),
    ("render", "렌더링 + 뷰포트"),
    ("interaction", "상호작용을 실제로"),
    ("semantic", "의미·맥락 판단"),
]

DEFECT_CODE = re.compile(r"\bD-\d+[a-z]?\b")


@dataclass(frozen=True)
class ParsedDefect:
    code: str
    category: str
    title: str
    location: str | None
    severity: str
    tier: str
    detection_method: str | None
    requires_viewport_w: int | None


def _cells(line: str) -> list[str]:
    return [c.strip() for c in line.strip().strip("|").split("|")]


def _strip_md(text: str) -> str:
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    return text.replace("`", "").strip()


def parse_tiers(markdown: str) -> dict[str, str]:
    """문서 끝 '난이도별 기대 성능' 목록에서 코드 → 층 을 만든다."""
    tiers: dict[str, str] = {}
    lines = markdown.splitlines()

    for tier, needle in TIER_HEADINGS:
        for i, line in enumerate(lines):
            if line.startswith("**") and needle in line:
                for follow in lines[i + 1 : i + 5]:
                    if follow.strip() == "":
                        break
                    for code in DEFECT_CODE.findall(follow):
                        tiers[code] = tier
                break

    return tiers


def parse_defects(markdown: str) -> list[ParsedDefect]:
    tiers = parse_tiers(markdown)

    defects: list[ParsedDefect] = []
    category = ""
    header: list[str] | None = None

    for line in markdown.splitlines():
        stripped = line.strip()

        if stripped.startswith("## "):
            category = stripped[3:].strip()
            header = None
            continue

        if not stripped.startswith("|"):
            header = None
            continue

        cells = _cells(stripped)

        if all(set(c) <= set("-: ") for c in cells):  # |---|---| 구분선
            continue

        if header is None:
            header = cells
            continue

        if not cells or not DEFECT_CODE.fullmatch(cells[0]):
            continue

        code = cells[0]
        if code not in tiers:
            raise ValueError(f"{code}: 난이도 층이 지정되지 않았습니다")

        # 절마다 열 구성이 다르고(A는 '탐지 방법', C는 '크기', G는 '재현 방법'),
        # 빈 칸을 아예 생략한 행도 있다(D-15). 열 번호로 읽으면 값이 한 칸씩 밀린다.
        # 심각도 값은 문서 전체에서 유일한 토큰이므로, 그 위치를 기준으로 좌우를 가른다.
        severity_idx = next(
            (i for i in range(len(cells) - 1, 0, -1) if cells[i] in SEVERITY_MAP), None
        )
        if severity_idx is None:
            raise ValueError(f"{code}: 심각도를 읽지 못했습니다 ({cells!r})")

        title = _strip_md(cells[1]) if len(cells) > 1 else ""
        middle = [_strip_md(c) for c in cells[2:severity_idx] if c]

        # C절에는 '크기' 열이 따로 있다. 제목에 합쳐야 정보가 사라지지 않는다.
        if "크기" in header and len(middle) == 2:
            title = f"{title} ({middle[0]})"
            location = middle[1]
        else:
            location = middle[0] if middle else None

        tail = [_strip_md(c) for c in cells[severity_idx + 1 :] if c]
        detection = tail[0] if tail else None

        defects.append(
            ParsedDefect(
                code=code,
                category=category,
                title=title,
                location=location,
                severity=SEVERITY_MAP[cells[severity_idx]],
                tier=tiers[code],
                detection_method=detection,
                # 기획서 6장: 375px에서만 드러나는 것은 1280 뷰포트에서 '잡을 수 없음'이다.
                requires_viewport_w=375 if detection and "375px" in detection else None,
            )
        )

    verify(defects)
    return defects


def verify(defects: list[ParsedDefect]) -> None:
    codes = [d.code for d in defects]
    dupes = sorted({c for c in codes if codes.count(c) > 1})
    if dupes:
        raise ValueError(f"중복된 결함 ID: {dupes}")

    if len(defects) != EXPECTED_TOTAL:
        raise ValueError(f"결함 {len(defects)}건. 기획서 기준 {EXPECTED_TOTAL}건이어야 합니다.")

    severity_counts: dict[str, int] = {}
    tier_counts: dict[str, int] = {}
    for d in defects:
        severity_counts[d.severity] = severity_counts.get(d.severity, 0) + 1
        tier_counts[d.tier] = tier_counts.get(d.tier, 0) + 1

    if severity_counts != EXPECTED_SEVERITY:
        raise ValueError(f"심각도 집계 불일치: {severity_counts} != {EXPECTED_SEVERITY}")
    if tier_counts != EXPECTED_TIER:
        raise ValueError(f"난이도 집계 불일치: {tier_counts} != {EXPECTED_TIER}")


if __name__ == "__main__":  # 단독 검증: python -m app.defects_parser <path>
    import sys
    from pathlib import Path

    parsed = parse_defects(Path(sys.argv[1]).read_text(encoding="utf-8"))
    print(f"결함 {len(parsed)}건 · 집계 검증 통과")
    for tier in ("static", "render", "interaction", "semantic"):
        print(f"  {tier:12s} {sum(1 for d in parsed if d.tier == tier):2d}건")
    blocked = [d.code for d in parsed if d.requires_viewport_w]
    print(f"  1280 뷰포트에서 잡을 수 없음: {blocked}")
