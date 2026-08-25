"""테스트 상세 화면이 쓰는 집계 — 여정 기록을 '경로'와 '다이어그램'으로 접는다.

화면(Figma 264:8033 / 276:3101)이 요구하는 것은 두 가지다.

1. 경로   — 같은 화면 순서를 밟은 사람끼리 묶은 목록. "동일한 화면 이동 순서 기준으로 묶었어요"
2. 다이어그램 — 같은 자료를 단계(열) × 화면(마디)으로 펼친 흐름도.

둘 다 같은 서명(signature)에서 나온다. 서명을 두 번 따로 만들면 두 화면의 숫자가
어긋나는 순간이 오기 때문에, 접는 규칙은 이 파일 하나에만 둔다.
"""

from __future__ import annotations

import uuid
from collections import Counter, defaultdict
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import Journey, Persona, Run, Step

#: 이탈로 세는 종료 사유. api.py 의 이탈률과 같은 정의를 쓴다 —
#: 예산 상한으로 우리가 끊은 것은 '포기'가 아니다(기획서 4장).
DROP_REASONS = ("gave_up", "loop_detected")

#: 카드 한 장에 나란히 놓는 화면 수. 넘으면 "+3" 으로 접는다 (Figma 264:8163).
CARD_SCREENS = 9


@dataclass
class Screen:
    key: str
    title: str
    url: str | None


@dataclass
class Walk:
    """여정 한 건을 화면 순서로 접은 것."""

    journey_id: uuid.UUID
    persona_id: uuid.UUID
    outcome: str  # 'success' | 'drop' | 'other'
    step_count: int
    screens: list[Screen] = field(default_factory=list)

    @property
    def signature(self) -> tuple[str, ...]:
        return tuple(s.key for s in self.screens)


def _screen_key(step: Step) -> str | None:
    """화면 이름. 답사가 붙인 screen_key 가 정본이고, 없으면 주소로 대신한다.

    주소도 없으면 그 스텝은 '어느 화면인지 모르는 스텝'이다. 모르는 것을 하나로 묶으면
    서로 다른 화면이 같은 경로로 접히므로, 아예 뺀다.
    """
    if step.screen_key:
        return step.screen_key
    if step.url:
        return step.url
    return None


def _outcome(journey: Journey) -> str:
    if journey.goal_achieved:
        return "success"
    if journey.termination_reason in DROP_REASONS:
        return "drop"
    return "other"


def load_walks(session: Session, test_id: uuid.UUID) -> list[Walk]:
    """테스트의 모든 여정을 화면 순서로 접어 온다.

    같은 화면에 연달아 머문 스텝(스크롤·입력)은 한 마디로 합친다. 합치지 않으면
    "장바구니 → 장바구니 → 장바구니" 가 서로 다른 경로가 되어 묶음이 흩어진다.
    """
    journeys = list(
        session.scalars(
            select(Journey)
            .join(Run, Run.id == Journey.run_id)
            .where(Run.test_id == test_id)
            .order_by(Journey.started_at)
        )
    )
    if not journeys:
        return []

    by_journey: dict[uuid.UUID, list[Step]] = defaultdict(list)
    steps = session.scalars(
        select(Step)
        .where(Step.journey_id.in_([j.id for j in journeys]))
        .order_by(Step.journey_id, Step.idx)
    )
    for step in steps:
        by_journey[step.journey_id].append(step)

    walks: list[Walk] = []
    for journey in journeys:
        screens: list[Screen] = []
        for step in by_journey.get(journey.id, []):
            # 기록만 남기고 실행되지 않은 행동은 화면을 바꾸지 않는다.
            if not step.executed:
                continue
            key = _screen_key(step)
            if key is None:
                continue
            if screens and screens[-1].key == key:
                continue
            screens.append(Screen(key=key, title=step.action_target or key, url=step.url))

        walks.append(
            Walk(
                journey_id=journey.id,
                persona_id=journey.persona_id,
                outcome=_outcome(journey),
                step_count=journey.step_count,
                screens=screens,
            )
        )

    return walks


# --------------------------------------------------------------------------- #
# 경로 카드
# --------------------------------------------------------------------------- #

#: 순위/모양으로 붙는 설명. Figma 의 문구를 그대로 쓴다.
LABEL_TOP = "가장 많이 사용한 경로"
LABEL_SECOND = "두 번째로 인기 있는 경로"
LABEL_SHORTEST = "가장 짧은 경로"
LABEL_LONGEST = "가장 많은 클릭 경로"
LABEL_TOP_DROP = "가장 많이 이탈한 경로"


def _label(rank: int, group: dict, shortest: int | None, longest: int | None, outcome: str) -> str:
    """설명은 붙일 근거가 있을 때만 붙인다.

    근거 없이 "가장 빠른 경로" 같은 말을 돌려가며 붙이면 화면은 그럴듯해 보이지만
    읽는 사람이 숫자와 대조했을 때 맞지 않는다.
    """
    if rank == 1:
        return LABEL_TOP_DROP if outcome == "drop" else LABEL_TOP
    if rank == 2:
        return LABEL_SECOND
    if shortest is not None and group["step_count"] == shortest:
        return LABEL_SHORTEST
    if longest is not None and group["step_count"] == longest:
        return LABEL_LONGEST
    return f"{rank}번째로 많은 경로"


def group_paths(walks: list[Walk], outcome: str) -> list[dict]:
    """같은 화면 순서를 밟은 사람끼리 묶어 인원 많은 순으로 준다."""
    picked = [w for w in walks if w.outcome == outcome and w.screens]
    if not picked:
        return []

    buckets: dict[tuple[str, ...], list[Walk]] = defaultdict(list)
    for walk in picked:
        buckets[walk.signature].append(walk)

    groups = []
    for signature, members in buckets.items():
        sample = members[0]
        # 스텝 수는 사람마다 다르다(같은 화면을 더 만졌을 수 있다). 대표값은 중앙값을 쓴다 —
        # 평균은 한 명이 40스텝을 헤매면 묶음 전체가 그 사람처럼 보인다.
        counts = sorted(w.step_count for w in members)
        median = counts[len(counts) // 2]
        groups.append(
            {
                "signature": list(signature),
                "persona_count": len(members),
                "step_count": median,
                "screens": [
                    {"key": s.key, "title": s.title, "url": s.url} for s in sample.screens
                ],
            }
        )

    groups.sort(key=lambda g: (-g["persona_count"], g["step_count"]))

    steps = [g["step_count"] for g in groups]
    shortest = min(steps) if len(groups) > 2 else None
    longest = max(steps) if len(groups) > 2 else None

    result = []
    for rank, group in enumerate(groups, start=1):
        result.append(
            {
                "rank": rank,
                "name": f"Path {rank}",
                "label": _label(rank, group, shortest, longest, outcome),
                "persona_count": group["persona_count"],
                "step_count": group["step_count"],
                "screens": group["screens"][:CARD_SCREENS],
                # 카드에 다 못 실은 화면 수. 0이면 화면이 "+0" 을 그리지 않는다.
                "more": max(0, len(group["screens"]) - CARD_SCREENS),
            }
        )
    return result


# --------------------------------------------------------------------------- #
# 네비게이션 다이어그램
# --------------------------------------------------------------------------- #

#: 열 개수 상한. 한 명이 40스텝을 헤매면 열이 40개가 되어 아무도 읽지 못한다.
MAX_COLUMNS = 12


def build_diagram(walks: list[Walk]) -> dict:
    """단계(열) × 화면(마디) 흐름도. 마디와 이음새마다 성공/이탈 인원을 함께 센다."""
    picked = [w for w in walks if w.screens]
    if not picked:
        return {"columns": [], "links": [], "total": 0}

    depth = min(MAX_COLUMNS, max(len(w.screens) for w in picked))

    nodes: dict[tuple[int, str], dict] = {}
    links: dict[tuple[str, str], dict] = {}

    for walk in picked:
        previous: str | None = None
        for position, screen in enumerate(walk.screens[:depth]):
            node_id = f"{position}:{screen.key}"
            node = nodes.setdefault(
                node_id,
                {
                    "id": node_id,
                    "column": position,
                    "key": screen.key,
                    "title": screen.title,
                    "count": 0,
                    "success": 0,
                    "drop": 0,
                },
            )
            node["count"] += 1
            if walk.outcome in ("success", "drop"):
                node[walk.outcome] += 1

            if previous is not None:
                link = links.setdefault(
                    (previous, node_id),
                    {"source": previous, "target": node_id, "count": 0, "success": 0, "drop": 0},
                )
                link["count"] += 1
                if walk.outcome in ("success", "drop"):
                    link[walk.outcome] += 1
            previous = node_id

    columns: list[list[dict]] = [[] for _ in range(depth)]
    for node in nodes.values():
        columns[node["column"]].append(node)
    for column in columns:
        column.sort(key=lambda n: -n["count"])

    return {
        "columns": [
            {"index": i, "label": "Start" if i == 0 else f"Step {i + 1}", "nodes": column}
            for i, column in enumerate(columns)
        ],
        "links": sorted(links.values(), key=lambda l: -l["count"]),
        "total": len(picked),
    }


# --------------------------------------------------------------------------- #
# 페르소나 이름
# --------------------------------------------------------------------------- #

#: 화면은 페르소나를 사람 이름으로 부른다(Figma 264:8753). DB 에는 코드(P001)만 있다.
#: 이름을 DB에 저장하면 같은 사람이 실행마다 다른 이름을 갖게 되므로, 코드에서 만든다 —
#: 코드가 같으면 이름도 항상 같다.
FAMILY = ("김", "이", "박", "최", "정", "강", "조", "윤", "장", "임", "한", "서", "배", "전")
GIVEN = (
    "승빈", "도현", "지훈", "민성", "현우", "유진", "민혁", "하늘", "다은", "준호",
    "서연", "예린", "진우", "은지", "민재", "서윤", "태윤", "지우", "하린", "성민",
)


def display_name(code: str) -> str:
    """P001 → '이승빈'. 성 14 × 이름 20 = 280 가지라 100명이 겹치지 않는다."""
    try:
        index = int(code.lstrip("P"))
    except ValueError:
        index = abs(hash(code))
    return FAMILY[index % len(FAMILY)] + GIVEN[(index // len(FAMILY)) % len(GIVEN)]


def persona_rows(session: Session, test_id: uuid.UUID, walks: list[Walk]) -> list[dict]:
    """사이드바 '페르소나' 탭 목록. 여정이 아직 없으면 결과 칸은 비운다."""
    personas = list(
        session.scalars(select(Persona).where(Persona.test_id == test_id).order_by(Persona.code))
    )
    by_persona = {w.persona_id: w for w in walks}

    rows = []
    for persona in personas:
        walk = by_persona.get(persona.id)
        rows.append(
            {
                "id": str(persona.id),
                "code": persona.code,
                "name": display_name(persona.code),
                "age_band": persona.age_band,
                "gender": persona.gender,
                "outcome": walk.outcome if walk else None,
                "step_count": walk.step_count if walk else None,
            }
        )
    return rows


def outcome_counts(walks: list[Walk]) -> Counter:
    return Counter(w.outcome for w in walks)
