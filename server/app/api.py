"""React 화면이 쓰는 읽기/쓰기 엔드포인트. 화면 하나가 엔드포인트 하나에 대응한다."""

from __future__ import annotations

import datetime as dt
import uuid

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .categories import CATEGORIES, normalize as normalize_category
from .connectivity import check_as_dict
from .db import get_session
from .estimates import DEFAULT_PAGE_COUNT, estimate
from .journeys import (
    DROP_REASONS,
    build_diagram,
    group_paths,
    load_walks,
    outcome_counts,
    persona_rows,
)
from .missions import analyze_as_dict
from .models import (
    Journey,
    Mission,
    Persona,
    PersonaSpec,
    Project,
    Run,
    RunScore,
    SiteMap,
    SiteVariant,
    Test,
)
from .personas import PersonaBuildError, assemble, popup_reachable_count
from .thumbnails import capture as capture_thumbnail

router = APIRouter(prefix="/api")


class ConnectivityIn(BaseModel):
    url: str


@router.post("/connectivity/check")
def connectivity_check(body: ConnectivityIn) -> dict:
    """[화면] 새 프로젝트 · 새 테스트의 '연결하기'.

    DB를 쓰지 않는다 — 주소를 저장하기 전에 눌러볼 수 있어야 한다.
    """
    return check_as_dict(body.url)


@router.get("/thumbnail")
async def thumbnail(url: str) -> Response:
    """[화면] 프로젝트 카드·테스트 목록의 웹 썸네일.

    사이트 첫 화면을 서버에서 PNG 로 찍어 준다. 프론트는 <img> 하나로 받으므로
    카드 안에서 무언가 움직일 여지가 없다. 찍지 못하면 404 — 화면이 기본 이미지로
    떨어진다. DB를 쓰지 않는다.
    """
    if not url.startswith(("http://", "https://")):
        raise HTTPException(status_code=400, detail="http(s) 주소만 찍을 수 있어요")

    png = await capture_thumbnail(url)
    if png is None:
        raise HTTPException(status_code=404, detail="썸네일을 찍지 못했어요")

    return Response(
        content=png,
        media_type="image/png",
        # 캐시는 서버에도 있지만, 목록을 오갈 때마다 다시 받아올 이유가 없다.
        headers={"Cache-Control": "public, max-age=3600"},
    )


class MissionAnalyzeIn(BaseModel):
    prompt: str


@router.post("/missions/analyze")
def analyze_mission(body: MissionAnalyzeIn) -> dict:
    """[화면] 미션 설정 — 문장을 검사하고 성공 기준을 만들어 준다.

    DB를 쓰지 않는다. 타이핑 중에도 불러야 하기 때문이다.
    """
    return analyze_as_dict(body.prompt)


# --------------------------------------------------------------------------- #
# 스키마
# --------------------------------------------------------------------------- #

class ProjectIn(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    category: str

    @field_validator("category")
    @classmethod
    def known_category(cls, value: str) -> str:
        # 목록 밖 값을 받아주면 카테고리별 묶기가 그 순간부터 어긋난다.
        resolved = normalize_category(value)
        if resolved is None:
            raise ValueError(f"카테고리는 {', '.join(CATEGORIES)} 중 하나여야 합니다")
        return resolved
    source: str = "web_link"
    device_preset: str = "16:9 데스크탑"
    target_url: str
    flow_map_path: str | None = None
    #: 연결 검사에서 받은 값. 카드 썸네일을 실제 화면으로 띄울지 판단한다.
    preview_embeddable: bool = False


def _as_utc(value: dt.datetime) -> dt.datetime:
    """시간대 없는 값은 UTC로 본다.

    SQLite 는 timestamptz 를 모르기 때문에 naive 로 돌아온다. 그대로 내보내면
    브라우저가 로컬 시각으로 읽어 KST 기준 9시간 어긋난 "9시간 전"이 찍힌다.
    """
    return value if value.tzinfo else value.replace(tzinfo=dt.timezone.utc)


class ProjectCard(BaseModel):
    id: uuid.UUID
    name: str
    category: str
    test_count: int
    last_activity_at: dt.datetime
    preview_url: str | None = None
    preview_embeddable: bool = False

    @field_validator("last_activity_at")
    @classmethod
    def to_utc(cls, value: dt.datetime) -> dt.datetime:
        return _as_utc(value)


class TestIn(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    device: str
    target_url: str


class MissionIn(BaseModel):
    prompt: str = Field(min_length=1, max_length=200)
    success_criteria: str
    auto_detect: bool = True


class PersonaSpecIn(BaseModel):
    age_band: str
    total: int = Field(ge=0)
    female_percent: int = Field(ge=0, le=100, default=50)
    gender_agnostic: bool = False
    enabled: bool = True


class TestStats(BaseModel):
    test_id: uuid.UUID
    name: str
    created_at: dt.datetime
    persona_count: int
    success_rate: float | None
    drop_rate: float | None

    @field_validator("created_at")
    @classmethod
    def to_utc(cls, value: dt.datetime) -> dt.datetime:
        return _as_utc(value)


# --------------------------------------------------------------------------- #
# [화면] 프로젝트 목록
# --------------------------------------------------------------------------- #

@router.get("/projects", response_model=list[ProjectCard])
def list_projects(session: Session = Depends(get_session)) -> list[ProjectCard]:
    rows = session.execute(
        select(
            Project.id,
            Project.name,
            Project.category,
            Project.preview_url,
            Project.preview_embeddable,
            func.count(Test.id).label("test_count"),
            func.coalesce(func.max(Test.created_at), Project.created_at).label("last_activity_at"),
        )
        .outerjoin(Test, Test.project_id == Project.id)
        .group_by(Project.id)
        .order_by(func.coalesce(func.max(Test.created_at), Project.created_at).desc())
    ).all()

    return [ProjectCard.model_validate(row._mapping) for row in rows]


@router.post("/projects", response_model=ProjectCard, status_code=201)
def create_project(body: ProjectIn, session: Session = Depends(get_session)) -> ProjectCard:
    project = Project(
        name=body.name,
        category=body.category,
        source=body.source,
        device_preset=body.device_preset,
        flow_map_path=body.flow_map_path,
        preview_url=body.target_url,
        preview_embeddable=body.preview_embeddable,
    )
    session.add(project)
    session.flush()

    # 기획서 5장: 대조군 없이는 정밀도를 잴 수 없다.
    # 프로젝트를 만들 때 두 변형을 함께 만들어, clean 없는 프로젝트가 생기지 않게 한다.
    for key, label, is_control in (("clean", "정상판", True), ("flawed", "결함판", False)):
        session.add(
            SiteVariant(
                project_id=project.id,
                key=key,
                label=label,
                base_url=f"{body.target_url.rstrip('/')}/{key}/",
                is_control=is_control,
                cart_storage_key=f"moji_cart_{key}",
            )
        )

    session.commit()
    return ProjectCard(
        id=project.id,
        name=project.name,
        category=project.category,
        test_count=0,
        last_activity_at=project.created_at,
        preview_url=project.preview_url,
        preview_embeddable=project.preview_embeddable,
    )


# --------------------------------------------------------------------------- #
# [화면] 프로젝트 상세
# --------------------------------------------------------------------------- #

@router.get("/projects/{project_id}")
def get_project(project_id: uuid.UUID, session: Session = Depends(get_session)) -> dict:
    project = session.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="프로젝트를 찾을 수 없습니다")

    stats = session.execute(
        select(
            func.count(func.distinct(Test.id)).label("test_count"),
            func.count(Journey.id).label("journeys"),
            func.count(Journey.id).filter(Journey.goal_achieved.is_(True)).label("achieved"),
            func.count(Journey.id)
            .filter(Journey.termination_reason.in_(DROP_REASONS))
            .label("dropped"),
        )
        .select_from(Test)
        .outerjoin(Run, Run.test_id == Test.id)
        .outerjoin(Journey, Journey.run_id == Run.id)
        .where(Test.project_id == project_id)
    ).one()

    journeys = stats.journeys or 0
    return {
        "id": str(project.id),
        "name": project.name,
        "category": project.category,
        "device_preset": project.device_preset,
        "viewport": {"w": project.viewport_w, "h": project.viewport_h},
        "preview_url": project.preview_url,
        "preview_embeddable": project.preview_embeddable,
        "test_count": stats.test_count or 0,
        # 여정이 하나도 없으면 비율은 0이 아니라 '아직 없음'이다. null 로 보내야
        # 화면이 "0.0%"라는 거짓 수치를 그리지 않는다.
        "success_rate": round(100 * stats.achieved / journeys, 1) if journeys else None,
        "drop_rate": round(100 * stats.dropped / journeys, 1) if journeys else None,
        "variants": [
            {"key": v.key, "label": v.label, "base_url": v.base_url, "is_control": v.is_control}
            for v in project.variants
        ],
    }


@router.get("/projects/{project_id}/tests", response_model=list[TestStats])
def list_tests(project_id: uuid.UUID, session: Session = Depends(get_session)) -> list[TestStats]:
    rows = session.execute(
        select(
            Test.id.label("test_id"),
            Test.name,
            Test.created_at,
            func.count(Journey.id).label("persona_count"),
            (
                100.0
                * func.count(Journey.id).filter(Journey.goal_achieved.is_(True))
                / func.nullif(func.count(Journey.id), 0)
            ).label("success_rate"),
            # 이탈률 = 포기 + 맴돌다 중단. 예산 상한으로 우리가 끊은 것은 세지 않는다
            # (기획서 4장: 그것을 '포기'로 적으면 통계가 오염된다).
            (
                100.0
                * func.count(Journey.id).filter(
                    Journey.termination_reason.in_(DROP_REASONS)
                )
                / func.nullif(func.count(Journey.id), 0)
            ).label("drop_rate"),
        )
        .outerjoin(Run, Run.test_id == Test.id)
        .outerjoin(Journey, Journey.run_id == Run.id)
        .where(Test.project_id == project_id)
        .group_by(Test.id)
        .order_by(Test.created_at.desc())
    ).all()

    return [TestStats.model_validate(row._mapping) for row in rows]


# --------------------------------------------------------------------------- #
# [화면] 새 테스트 · 미션 · 페르소나
# --------------------------------------------------------------------------- #

@router.post("/projects/{project_id}/tests", status_code=201)
def create_test(project_id: uuid.UUID, body: TestIn, session: Session = Depends(get_session)) -> dict:
    test = Test(project_id=project_id, **body.model_dump())
    session.add(test)
    session.commit()
    return {"id": test.id}


@router.put("/tests/{test_id}/mission")
def upsert_mission(test_id: uuid.UUID, body: MissionIn, session: Session = Depends(get_session)) -> dict:
    mission = session.scalar(select(Mission).where(Mission.test_id == test_id))
    if mission is None:
        mission = Mission(test_id=test_id, **body.model_dump())
        session.add(mission)
    else:
        for key, value in body.model_dump().items():
            setattr(mission, key, value)
    session.commit()
    return {"id": mission.id}


@router.put("/tests/{test_id}/persona-specs")
def replace_persona_specs(
    test_id: uuid.UUID, body: list[PersonaSpecIn], session: Session = Depends(get_session)
) -> dict:
    existing = {
        s.age_band: s
        for s in session.scalars(select(PersonaSpec).where(PersonaSpec.test_id == test_id))
    }
    for item in body:
        row = existing.get(item.age_band)
        if row is None:
            session.add(PersonaSpec(test_id=test_id, **item.model_dump()))
        else:
            for key, value in item.model_dump().items():
                setattr(row, key, value)

    session.commit()
    return {"total": sum(i.total for i in body if i.enabled)}


@router.post("/tests/{test_id}/personas/assemble")
def build_personas(test_id: uuid.UUID, session: Session = Depends(get_session)) -> dict:
    try:
        personas = assemble(session, test_id)
    except PersonaBuildError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    session.commit()
    return {
        "count": len(personas),
        "unique_pairs": len({(p.trait_combo_id, p.goal_id) for p in personas}),
        # 이 수가 0이면 D-26(10초 팝업)은 '못 잡은 것'이 아니라 '마주친 적 없는 것'이 된다.
        "popup_reachable": popup_reachable_count(personas),
    }


# --------------------------------------------------------------------------- #
# [화면] 확인
# --------------------------------------------------------------------------- #

@router.get("/tests/{test_id}/review")
def review(test_id: uuid.UUID, session: Session = Depends(get_session)) -> dict:
    test = session.get(Test, test_id)
    if test is None:
        raise HTTPException(status_code=404, detail="테스트를 찾을 수 없습니다")

    mission = session.scalar(select(Mission).where(Mission.test_id == test_id))
    specs = list(session.scalars(select(PersonaSpec).where(PersonaSpec.test_id == test_id)))
    persona_count = session.scalar(
        select(func.count(Persona.id)).where(Persona.test_id == test_id)
    ) or sum(s.total for s in specs if s.enabled)

    # 답사가 확인한 화면 수가 있으면 그 값으로, 없으면 기본값으로 추정한다.
    page_count = session.scalar(
        select(SiteMap.screens_found)
        .join(SiteVariant, SiteVariant.id == SiteMap.site_variant_id)
        .where(SiteVariant.project_id == test.project_id)
        .order_by(SiteMap.created_at.desc())
        .limit(1)
    )

    est = estimate(persona_count, page_count or DEFAULT_PAGE_COUNT)
    return {
        "project": {"id": str(test.project_id)},
        "test": {"id": str(test.id), "name": test.name, "device": test.device},
        "mission": None if mission is None else {
            "prompt": mission.prompt,
            "success_criteria": mission.success_criteria,
        },
        "personas": {
            "total": persona_count,
            "breakdown": [
                {"age_band": s.age_band, "total": s.total, **s.split()}
                for s in specs
                if s.enabled and s.total > 0
            ],
        },
        "estimate": {
            "minutes": est.minutes,
            "tokens": est.tokens,
            "page_count": est.page_count,
            "vision_calls": est.vision_calls,
            "usd": est.usd,
            # 화면에서 '약'을 붙일지 결정하는 값. 실측 전에는 추정치임을 밝혀야 한다.
            "measured": est.measured,
            "formula": est.formula,
        },
    }


# --------------------------------------------------------------------------- #
# 실행
# --------------------------------------------------------------------------- #

@router.post("/tests/{test_id}/runs", status_code=201)
def start_run(test_id: uuid.UUID, session: Session = Depends(get_session)) -> dict:
    """[화면] 확인의 '테스트 하기'.

    실제 탐색은 파이프라인(run.py)이 돌린다. 여기서는 실행 한 건을 열고
    페르소나별 여정 자리를 만들어 둘 뿐이다 — 진행률은 그 여정들이 채워진다.
    """
    test = session.get(Test, test_id)
    if test is None:
        raise HTTPException(status_code=404, detail="테스트를 찾을 수 없습니다")

    try:
        personas = assemble(session, test_id)
    except PersonaBuildError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    variant = session.scalar(
        select(SiteVariant).where(
            SiteVariant.project_id == test.project_id, SiteVariant.is_control.is_(False)
        )
    )
    if variant is None:
        raise HTTPException(status_code=422, detail="결함판 변형이 없습니다")

    # 화면에서 시작하는 실행은 A(결함판 + 지도)다. 나머지 B/C/D는 검증 계획용이라
    # 파이프라인이 따로 연다. 같은 팔을 두 번 열면 어느 쪽이 발표 수치인지 알 수 없다.
    run = session.scalar(select(Run).where(Run.test_id == test_id, Run.arm == "A"))
    if run is None:
        run = Run(test_id=test_id, site_variant_id=variant.id, arm="A", map_enabled=False)
        session.add(run)

    run.persona_count = len(personas)
    run.status = "running"
    run.started_at = dt.datetime.now(dt.timezone.utc)
    # 기획서 7장: 2명 이상은 예상 호출 수를 보여준 뒤 확인을 받는다.
    # 확인 화면을 거쳐 눌린 버튼이므로 그 사실을 여기 남긴다.
    run.confirmed_at = dt.datetime.now(dt.timezone.utc)
    session.flush()

    existing = {
        j.persona_id for j in session.scalars(select(Journey).where(Journey.run_id == run.id))
    }
    for persona in personas:
        if persona.id not in existing:
            session.add(Journey(run_id=run.id, persona_id=persona.id))

    session.commit()
    return {"run_id": str(run.id), "persona_count": run.persona_count, "status": run.status}


@router.get("/runs/active")
def active_run(session: Session = Depends(get_session)) -> dict | None:
    """[화면] 진행중 배너. 돌고 있는 실행이 없으면 null 을 준다."""
    row = session.execute(
        select(Run, Test, Project)
        .join(Test, Test.id == Run.test_id)
        .join(Project, Project.id == Test.project_id)
        .where(Run.status == "running")
        .order_by(Run.started_at.desc())
        .limit(1)
    ).first()

    if row is None:
        return None

    run, test, project = row
    done = session.scalar(
        select(func.count(Journey.id)).where(
            Journey.run_id == run.id, Journey.finished_at.is_not(None)
        )
    ) or 0

    return {
        "run_id": str(run.id),
        "project_id": str(project.id),
        "project_name": project.name,
        "test_name": test.name,
        "done": done,
        "total": run.persona_count,
    }


# --------------------------------------------------------------------------- #
# [화면] 테스트 상세 — 미션 경로 · 다이어그램 · 페르소나
# --------------------------------------------------------------------------- #

def _load_test(test_id: uuid.UUID, session: Session) -> Test:
    test = session.get(Test, test_id)
    if test is None:
        raise HTTPException(status_code=404, detail="테스트를 찾을 수 없습니다")
    return test


@router.get("/tests/{test_id}")
def test_detail(test_id: uuid.UUID, session: Session = Depends(get_session)) -> dict:
    """상단 제목 · 미션 문장 · 지표 세 칸."""
    test = _load_test(test_id, session)
    project = session.get(Project, test.project_id)
    mission = session.scalar(select(Mission).where(Mission.test_id == test_id))

    stats = session.execute(
        select(
            func.count(Journey.id).label("journeys"),
            func.count(Journey.id).filter(Journey.goal_achieved.is_(True)).label("achieved"),
            func.count(Journey.id)
            .filter(Journey.termination_reason.in_(DROP_REASONS))
            .label("dropped"),
            func.avg(Journey.step_count)
            .filter(Journey.goal_achieved.is_(True))
            .label("success_steps"),
        )
        .select_from(Journey)
        .join(Run, Run.id == Journey.run_id)
        .where(Run.test_id == test_id)
    ).one()

    journeys = stats.journeys or 0
    persona_total = session.scalar(
        select(func.count(Persona.id)).where(Persona.test_id == test_id)
    ) or 0

    return {
        "id": str(test.id),
        "name": test.name,
        "device": test.device,
        "created_at": _as_utc(test.created_at),
        "project": {
            "id": str(test.project_id),
            "name": project.name if project else "",
            "preview_url": project.preview_url if project else None,
        },
        "mission": None if mission is None else {
            "prompt": mission.prompt,
            "success_criteria": mission.success_criteria,
        },
        "persona_total": persona_total,
        "journey_count": journeys,
        # 여정이 없으면 0% 가 아니라 '아직 없음'이다 — 프로젝트 상세와 같은 규칙.
        "success_rate": round(100 * stats.achieved / journeys, 1) if journeys else None,
        "drop_rate": round(100 * stats.dropped / journeys, 1) if journeys else None,
        "avg_success_steps": round(float(stats.success_steps), 2) if stats.success_steps else None,
    }


@router.get("/tests/{test_id}/paths")
def test_paths(test_id: uuid.UUID, session: Session = Depends(get_session)) -> dict:
    """'경로' 보기. 성공/이탈 두 묶음을 한 번에 준다 — 탭을 눌러도 다시 부르지 않는다."""
    _load_test(test_id, session)
    walks = load_walks(session, test_id)
    counts = outcome_counts(walks)
    total = len(walks)

    def share(kind: str) -> dict:
        count = counts.get(kind, 0)
        return {"count": count, "percent": round(100 * count / total) if total else 0}

    return {
        "total": total,
        "success": share("success"),
        "drop": share("drop"),
        "paths": {
            "success": group_paths(walks, "success"),
            "drop": group_paths(walks, "drop"),
        },
    }


@router.get("/tests/{test_id}/diagram")
def test_diagram(test_id: uuid.UUID, session: Session = Depends(get_session)) -> dict:
    """'다이어그램' 보기. 같은 여정을 단계 × 화면으로 펼친다."""
    _load_test(test_id, session)
    return build_diagram(load_walks(session, test_id))


@router.get("/tests/{test_id}/personas")
def test_personas(test_id: uuid.UUID, session: Session = Depends(get_session)) -> dict:
    """사이드바 '페르소나' 탭."""
    _load_test(test_id, session)
    rows = persona_rows(session, test_id, load_walks(session, test_id))
    return {"total": len(rows), "items": rows}


# --------------------------------------------------------------------------- #
# 검증 계획 A/B/C/D
# --------------------------------------------------------------------------- #

@router.get("/tests/{test_id}/ablation")
def ablation(test_id: uuid.UUID, session: Session = Depends(get_session)) -> list[dict]:
    rows = session.execute(
        select(Run.arm, SiteVariant.key, Run.map_enabled, Run.status, RunScore)
        .join(SiteVariant, SiteVariant.id == Run.site_variant_id)
        .outerjoin(RunScore, RunScore.run_id == Run.id)
        .where(Run.test_id == test_id)
        .order_by(Run.arm)
    ).all()

    return [
        {
            "arm": arm,
            "variant": variant,
            "map_enabled": map_enabled,
            "status": status,
            "recall": float(score.recall) if score and score.recall is not None else None,
            "precision": float(score.precision) if score and score.precision is not None else None,
            "fp_rate": float(score.fp_rate) if score and score.fp_rate is not None else None,
        }
        for arm, variant, map_enabled, status, score in rows
    ]
