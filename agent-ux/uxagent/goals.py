"""목표 생성 — 지도를 보고 '사람이 하려는 일' 11개를 만든다.

목표는 결함 목록이 아니다. "결제 버튼이 눌리는지 확인한다" 같은 문장이
목표로 들어가면 100명 전원이 그 결함을 찾으러 가고, 적중률은 오르지만
그건 우리가 미리 답을 알려준 것이다. 답사자에게 걸었던 것과 같은 금칙어
필터를 목표에도 건다 (survey.BANNED_WORDS 재사용).

세 유형
  A 구매 완수   — 담아서 주문까지
  B 정보 확인   — 페이지 안의 정보만 확인하고 이탈
  C 중단·재개   — 담아둔 장바구니가 있는 상태에서 시작

유형 B에 주의: 이 테스트베드에는 /returns /shipping /bundles 가 **없다.**
'배송정책 페이지를 찾아본다' 류는 원리적으로 실패하는 목표라 마찰이 아니라
잡음이 된다. 프롬프트로 막고, start_path 가 지도에 없으면 코드가 거부한다.
"""
from __future__ import annotations

from . import config, discover
from .persona import DEFAULT_SEED, TWO_ITEM_SEED
from .survey import _scan

MAX_TEXT = 60   # 페르소나 프롬프트 200자 상한을 지키려면 목표 한 줄이 짧아야 한다


# ── 기본 목표 (--mock 및 지도 없이 돌릴 때) ────────────────────────
# 사이트 사실에 맞춰 손으로 쓴 것이다. 상품 12종, 품절 id=7·12,
# 무료배송 5만원, 결제는 3단계 브레드크럼.
MOCK_GOALS = [
    {"id": "G01", "type": "A", "start_path": "/index.html",
     "text": "코튼 셔츠를 장바구니에 담아 주문까지 마친다.",
     "success": "주문 완료 화면에 도달"},
    {"id": "G02", "type": "A", "start_path": "/list.html",
     "text": "신발 중에서 스니커즈 한 켤레를 골라 결제한다.",
     "success": "신발 카테고리 상품으로 주문 완료"},
    {"id": "G03", "type": "A", "start_path": "/list.html",
     "text": "무료배송이 되도록 담아서 주문을 마친다.",
     "success": "합계 5만원 이상으로 주문 완료"},
    {"id": "G04", "type": "A", "start_path": "/product.html?id=7",
     "text": "워시드 후디를 사려고 한다.",
     "success": "품절을 확인하고 대체품 구매 또는 이탈"},
    {"id": "G05", "type": "A", "start_path": "/index.html",
     "text": "액세서리 두 가지를 한 번에 주문한다.",
     "success": "액세서리 2종이 담긴 상태로 주문 완료"},
    {"id": "G06", "type": "B", "start_path": "/index.html",
     "text": "배송비가 무료가 되는 금액을 확인하고 나간다.",
     "success": "5만원 기준을 말하고 종료"},
    {"id": "G07", "type": "B", "start_path": "/list.html",
     "text": "스니커즈에 260 사이즈가 있는지 확인만 한다.",
     "success": "사이즈 목록을 확인하고 종료"},
    {"id": "G08", "type": "B", "start_path": "/cart.html",
     "text": "장바구니의 총 결제금액을 확인하고 나간다.",
     "success": "배송비 포함 합계를 말하고 종료",
     "seed_state": DEFAULT_SEED},
    {"id": "G09", "type": "C", "start_path": "/index.html",
     "text": "지난번에 담아둔 장바구니를 이어서 결제한다.",
     "success": "담긴 상품 그대로 주문 완료",
     "seed_state": TWO_ITEM_SEED},
    {"id": "G10", "type": "C", "start_path": "/cart.html",
     "text": "담아둔 것 중 하나를 빼고 나머지만 주문한다.",
     "success": "1건 삭제 후 주문 완료",
     "seed_state": TWO_ITEM_SEED},
    {"id": "G11", "type": "C", "start_path": "/cart.html",
     "text": "담아둔 상품의 수량을 2개로 바꿔 주문한다.",
     "success": "수량 변경이 합계에 반영된 뒤 주문 완료",
     "seed_state": DEFAULT_SEED},
]


# ── 검사 ──────────────────────────────────────────────────────────

def validate(goals: list[dict], paths: set[str]) -> list[str]:
    """LLM 이 만든 목표를 코드가 검사한다. LLM 에게 자기 검증을 맡기지 않는다.

    경로는 **템플릿 단위로** 대조한다. 지도는 product.html?id=1..12 를 한 줄로
    접어두므로(discover.template_key) 지도에 실린 대표 경로는 ?id=3 하나뿐이다.
    문자열로 비교하면 '품절 상품(?id=7)을 사러 간다' 같은 정당한 목표가
    거부된다. 마찰을 일부러 만드는 목표를 검사기가 지우면 안 된다.
    """
    templates = {discover.template_key(p) for p in paths}
    issues = []
    if len(goals) != config.N_GOALS:
        issues.append("목표가 %d개입니다. 16조합과 서로소인 %d개여야 100명이 "
                      "서로 다른 쌍을 받습니다." % (len(goals), config.N_GOALS))

    ids, mix = set(), {t: 0 for t in config.GOAL_TYPES}
    for g in goals:
        gid = g.get("id", "?")
        if gid in ids:
            issues.append("%s: id 중복" % gid)
        ids.add(gid)

        t = g.get("type")
        if t not in config.GOAL_TYPES:
            issues.append("%s: 알 수 없는 유형 %r" % (gid, t))
        else:
            mix[t] += 1

        text = str(g.get("text") or "")
        if not text:
            issues.append("%s: text 없음" % gid)
        if len(text) > MAX_TEXT:
            issues.append("%s: 목표가 %d자 (상한 %d자)" % (gid, len(text), MAX_TEXT))
        for w in _scan(text):
            # 결함을 미리 알려주는 문장. 이게 통과하면 적중률이 아니라
            # 우리가 심어둔 답을 세는 것이 된다.
            issues.append("%s: 판단 표현 '%s' — 목표는 할 일이지 결함이 아닙니다" % (gid, w))

        sp = g.get("start_path")
        if discover.template_key(str(sp or "")) not in templates:
            issues.append("%s: 지도에 없는 시작 경로 %r (가능한 템플릿: %s)"
                          % (gid, sp, sorted(templates)))

    if mix != config.GOAL_MIX and len(goals) == config.N_GOALS:
        issues.append("유형 분포 %s, 기대 %s" % (mix, config.GOAL_MIX))
    return issues


def attach_seeds(goals: list[dict]) -> list[dict]:
    """유형 C 의 장바구니는 코드가 채운다.

    지도 = 서술(LLM) / 상태 = 코드. 답사에서 측정값을 LLM 에게 맡기지 않은
    것과 같은 이유다. LLM 이 지어낸 장바구니는 상품 id 나 가격이 틀려도
    문장 검사를 그냥 통과하고, 틀린 채로 100명에게 배포된다.
    """
    out = []
    for i, g in enumerate(goals):
        g = dict(g)
        if g["type"] == "C" and not g.get("seed_state"):
            g["seed_state"] = TWO_ITEM_SEED if i % 2 == 0 else DEFAULT_SEED
        out.append(g)
    return out


# ── 프롬프트 ──────────────────────────────────────────────────────

SYSTEM = """당신은 쇼핑몰에서 사람들이 하려는 일을 목록으로 만드는 사람입니다.

[절대 규칙]
- 사이트의 문제점을 쓰지 마세요. 당신은 결함을 모릅니다.
- "확인해본다", "작동하는지 본다" 처럼 검사하는 문장이 아니라,
  그냥 사람이 하려는 일을 쓰세요.
- 지도에 없는 페이지를 요구하지 마세요. 없는 페이지로 보내면 목표가 아니라
  막다른 길이 됩니다.
- 목표 한 줄은 60자 이내. 배경 설명 금지.

반드시 한국어로 작성하세요."""

USER_TMPL = """아래는 어떤 쇼핑몰의 지도입니다.

{pages}

이 사이트에서 사람들이 하려는 일 {n}개를 만드세요. 유형은 셋입니다.

- A ({a}개) 구매 완수: 상품을 골라 주문까지 끝낸다
- B ({b}개) 정보 확인: 페이지 안의 정보만 확인하고 나간다
       (별도의 안내 페이지는 이 사이트에 없습니다. 지금 보이는 화면 안에서
        확인할 수 있는 것이어야 합니다)
- C ({c}개) 중단·재개: 이미 장바구니에 담아둔 것이 있는 상태에서 시작한다
       (무엇이 담겨 있는지는 쓰지 마세요. 별도로 채워집니다)

start_path 는 반드시 위 지도에 있는 경로 중 하나여야 합니다.

[출력 형식 — JSON만, 다른 말 금지]
{{"goals": [
  {{"id": "G01", "type": "A", "start_path": "/index.html",
   "text": "...", "success": "무엇이 되면 성공인지 한 줄"}}
]}}"""


def map_digest(site_map: dict) -> str:
    """지도에서 목표 생성에 필요한 것만 추린다. 측정값은 애초에 지도에 없다."""
    out = []
    for p in site_map.get("pages", []):
        names = ", ".join(e.get("name", "?") for e in (p.get("elements") or [])[:10])
        out.append("- %s  %s\n    배치: %s\n    요소: %s"
                   % (p["path"], p.get("title", ""), p.get("layout", ""), names))
    return "\n".join(out)


def generate(client, site_map: dict, *, model: str, usage, mock: bool) -> list[dict]:
    """지도 -> 목표 11개. mock 이면 손으로 쓴 기본 목록."""
    if mock:
        return [dict(g) for g in MOCK_GOALS]

    from .llm import chat_json

    body = chat_json(
        client,
        model=model,
        system=SYSTEM,
        user=USER_TMPL.format(
            pages=map_digest(site_map), n=config.N_GOALS,
            a=config.GOAL_MIX["A"], b=config.GOAL_MIX["B"], c=config.GOAL_MIX["C"]),
        temperature=config.TEMP_GOALS,
        usage=usage,
    )
    goals = body.get("goals") or []
    for i, g in enumerate(goals, 1):
        g.setdefault("id", "G%02d" % i)
    return goals
