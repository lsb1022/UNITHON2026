"""답사 페르소나 — 스크린샷을 찍어가며 **직접 조작해** 사이트 설명서를 만든다.

기존 `survey.py` 는 페이지마다 한 번씩 들러 사진을 찍는 정적 촬영이다.
링크로 갈 수 있는 곳만 찍히고, **눌러야 나오는 화면은 원리적으로 못 본다.**
우리 테스트베드에서 `complete.html` 이 그랬고, 그건 로컬 디렉터리 목록으로
겨우 메웠다. 남의 사이트에서는 그 층이 꺼지므로 그냥 없는 페이지가 된다.

이 모듈은 답사자를 **한 명의 탐험가**로 만든다. 스텝마다 스크린샷을 찍고,
본 것을 기록하고, 다음에 무엇을 눌러볼지 스스로 정한다. 결제를 한 번
완주하면 결제 완료 화면이 설명서에 들어간다.

호출 수는 페르소나 한 명분이다. 40~60스텝이면 이미지 호출 40~60회이고,
뒤따르는 100명은 이 설명서만 읽으므로 이미지를 한 장도 쓰지 않는다.

## 성격은 주되 판단은 금지한다

탐험가에게 성격을 준다. 성격은 **어디를 눌러볼지**를 정한다.
하지만 기록은 여전히 사실만 남긴다. 답사자가 "여기 불편함"이라고 적으면
100명 전원이 그 문제를 '발견'하고, 적중률 100%는 1명이 찾은 것을 100번
복사한 값이 된다. `survey.BANNED_WORDS` 필터를 그대로 건다.

## 측정값은 여전히 코드가 만든다

스크린샷을 본 모델은 대비를 계산하지 못하고 좌표를 픽셀로 못 읽는다.
설명서에는 배치와 요소 이름만 들어가고, 수치는 매 스텝 `snapshot.py` 가 뽑는다.
"""
from __future__ import annotations

from . import config, discover
from .llm import chat_json_any
from .survey import validate_page

# 탐험가의 성격. 목표가 아니라 '어디를 눌러볼지'의 취향이다.
PERSONALITY = ("구석구석 눌러보는 성격이다. 아직 안 가본 곳을 먼저 찾고, "
               "끝까지 가봐야 직성이 풀린다.")

SYSTEM = """당신은 어떤 쇼핑몰을 처음부터 끝까지 돌아보며 설명서를 만드는 사람입니다.
%s

[하는 일]
화면을 보고 (1) 지금 화면이 어떻게 생겼는지 적고 (2) 다음에 무엇을 눌러볼지 정합니다.

[절대 규칙 — 평가하지 않습니다]
다음 표현을 쓰지 마세요: 불편하다, 헷갈린다, 찾기 어렵다, 이상하다,
작동하지 않는다, 문제가 있다, 개선이 필요하다, 너무 (길다/작다/많다),
부족하다, 좋다, 나쁘다, 명확하다, 모호하다, 복잡하다, 번거롭다.

기준은 "카메라로 찍어서 확인할 수 있는 사실인가"입니다.
확인 가능하면 적고, 해석이 필요하면 쓰지 마세요.

[수치를 지어내지 마세요]
색 대비, 픽셀 좌표, 요소 크기는 적지 않습니다. 별도의 계산 모듈이 정확히 잽니다.
당신은 눈에 보이는 배치와 요소의 이름만 서술하세요.

[돌아다니는 법]
- 링크만 따라가지 마세요. 눌러야 나오는 화면(장바구니 담기, 결제 진행,
  팝업, 단계 이동)도 설명서에 들어가야 합니다.
- 필요하면 상품을 담고 결제를 끝까지 진행해 보세요. 실제 주문이 아닙니다.
- 이미 적은 화면에 다시 오면 record 는 null 로 두고 다음 곳으로 가세요.
- 더 볼 곳이 없으면 action.type 을 "done" 으로 하세요.

반드시 한국어로 작성하세요.

[출력 형식 — JSON만, 다른 말 금지]
{"record": {"layout": "화면 배치 한두 문장",
            "elements": [{"name": "...", "type": "버튼", "where": "우측 상단"}],
            "steps": null},
 "thought": "다음에 무엇을 왜 해보려는지",
 "action": {"type": "click", "target": "button_3"}}""" % PERSONALITY


USER_TMPL = """[지금 화면]
{snapshot}

[이미 설명서에 적은 화면] {recorded}
[아직 안 가본 것으로 보이는 곳] {todo}

[방금 한 일]
{history}

[할 수 있는 행동] click, type, select, scroll, back, goto, wait, done

이 화면이 설명서에 없으면 record 를 채우고, 있으면 record 는 null 로 두세요.
JSON 하나만 출력하세요."""


def build_user(snap_text: str, recorded: list[str], todo: list[str],
               history: str) -> str:
    return USER_TMPL.format(
        snapshot=snap_text,
        recorded=", ".join(recorded) or "(없음)",
        todo=", ".join(todo[:8]) or "(모름)",
        history=history or "(아직 아무것도 하지 않았습니다)",
    )


def decide(client, *, models: list[str], snap_text: str, shot: bytes | None,
           recorded: list[str], todo: list[str], history: str, usage) -> dict:
    body = chat_json_any(
        client,
        models=models,
        system=SYSTEM,
        user=build_user(snap_text, recorded, todo, history),
        images=[shot] if shot else None,
        temperature=config.TEMP_SURVEY,
        usage=usage,
    )
    action = body.get("action") or {}
    if isinstance(action, str):
        action = {"type": action}
    action.setdefault("type", "scroll")
    return {"record": body.get("record"),
            "thought": str(body.get("thought") or "").strip() or "(생각 없음)",
            "action": action}


# ── 모의 탐험가 (--mock) ──────────────────────────────────────────
# LLM 없이 루프가 도는지 확인하기 위한 것. 앞으로 나아가는 낱말을 우선한다.
_FORWARD = ("담기", "주문", "결제", "구매", "다음", "계속", "완료")
_CLOSE = ("닫기", "close", "×", "✕")
# 헤더 내비게이션은 어느 화면에나 있다. 이것만 누르면 몇 화면에서 맴돈다.
# 눌러야 나오는 화면(상품 -> 담기 -> 결제)에 닿으려면 뒤로 미뤄야 한다.
_NAV = ("MOJI", "홈", "전체 상품", "상의", "하의", "신발", "액세서리", "장바구니")
_FILL = {"text": "홍길동", "tel": "01012345678", "email": "test@example.com",
         "number": "1", "search": "셔츠", "password": "test1234"}
_FILLABLE = tuple(_FILL)


def mock_decide(snap: dict, recorded: set[str], visited: set[tuple]) -> dict:
    key = discover.template_key(snap["url"])
    record = None
    if key not in recorded:
        record = {
            "layout": "(%s 자리표시자) 상단 헤더, 중앙 본문, 하단 푸터로 구성" % key,
            "elements": [{"name": e["text"] or e["id"], "type": e["tag"],
                          "where": "위쪽" if not e["below_fold"] else "아래쪽"}
                         for e in snap["elements"][:6]],
            "steps": None,
        }

    els = [e for e in snap["elements"]
           if (snap["url"], e["id"]) not in visited and not e["occluded"]]
    blocked = sum(1 for e in snap["elements"] if e["occluded"])
    if blocked and blocked * 2 >= len(snap["elements"]):
        for e in els:
            if any(w in (e["text"] or "").lower() for w in _CLOSE):
                return {"record": record, "thought": "가리고 있는 것을 닫습니다.",
                        "action": {"type": "click", "target": e["id"]}}
    # 빈 입력칸이 있으면 먼저 채운다. 결제 완료 화면은 폼을 통과해야만 나오고,
    # 그 화면에 닿는 것이 이 답사기를 만든 이유다.
    for e in els:
        if e.get("input_type") in _FILLABLE and not (e.get("value") or "").strip():
            return {"record": record,
                    "thought": "'%s' 칸을 채웁니다." % (e["text"] or e["id"]),
                    "action": {"type": "type", "target": e["id"],
                               "value": _FILL[e["input_type"]]}}
    # 체크 안 된 선택지(약관 동의, 결제수단)를 고른다. 이걸 빼먹으면 폼이
    # 통과하지 않고, 폼이 통과하지 않으면 결제 완료 화면에 영영 못 간다.
    for e in els:
        if e.get("checked") is False:
            return {"record": record,
                    "thought": "'%s' 를 선택합니다." % (e["text"] or e["id"]),
                    "action": {"type": "click", "target": e["id"]}}

    # 앞으로 가는 버튼은 '이미 눌러봤다'고 건너뛰지 않는다. 폼을 채우기 전에
    # 한 번 눌러 실패했더라도, 채운 뒤에는 다시 눌러야 통과한다.
    for e in snap["elements"]:
        if e["occluded"]:
            continue
        if e["tag"] in ("button", "input") and any(w in (e["text"] or "") for w in _FORWARD):
            return {"record": record, "thought": "'%s' 를 눌러 다음 단계로." % e["text"],
                    "action": {"type": "click", "target": e["id"]}}
    for e in els:
        if any(w in (e["text"] or "") for w in _FORWARD):
            return {"record": record, "thought": "'%s' 를 눌러 다음 단계로." % e["text"],
                    "action": {"type": "click", "target": e["id"]}}
    body = [e for e in els if e["tag"] == "a"
            and (e["text"] or "").strip() not in _NAV]
    if body:
        return {"record": record,
                "thought": "'%s' 를 열어봅니다." % (body[0]["text"] or body[0]["id"]),
                "action": {"type": "click", "target": body[0]["id"]}}
    links = [e for e in els if e["tag"] == "a"]
    if links:
        return {"record": record,
                "thought": "'%s' 로 가봅니다." % (links[0]["text"] or links[0]["id"]),
                "action": {"type": "click", "target": links[0]["id"]}}
    return {"record": record, "thought": "아래를 더 봅니다.", "action": {"type": "scroll"}}


# ── 설명서 조립 ───────────────────────────────────────────────────

def page_entry(snap: dict, record: dict, root: str, found_by: str) -> dict:
    """설명서 한 장. survey.py 가 만드는 것과 같은 형식이어야 한다.

    형식이 어긋나면 generate.py 와 run.py 를 둘 다 고쳐야 하고, 두 답사기의
    지도를 비교할 수도 없게 된다.
    """
    return {
        "path": discover.rel_path(snap["url"], root),
        "template": discover.template_key(snap["url"]),
        "title": snap["title"],
        "found_by": found_by,
        "layout": (record or {}).get("layout"),
        "elements": (record or {}).get("elements") or [],
        "links_to": [],          # 아래에서 실제 이동 기록으로 채운다
        "steps": (record or {}).get("steps"),
    }


def clean_record(record: dict | None) -> tuple[dict | None, list[str]]:
    """판단 표현이 섞였는지 코드가 검사한다. LLM에게 자기 검증을 맡기지 않는다."""
    if not record:
        return None, []
    issues = validate_page({"path": "(현재 화면)", "title": "",
                            "layout": record.get("layout"),
                            "elements": record.get("elements") or [],
                            "steps": record.get("steps")})
    return record, issues
