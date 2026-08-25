"""답사 에이전트 — 사이트의 '사실'만 기록해 지도를 만든다.

가장 중요한 규칙: 답사자는 판단하지 않는다.
답사자가 "슬라이더가 작동하지 않음"이라고 적으면 100명 전원이 그 문제를
'발견'한다. 적중률 100%가 나오지만 1명이 찾은 걸 100번 복사한 것이고,
페르soナ가 존재할 이유가 사라진다. 그래서 금칙어를 코드로 검사한다.
(LLM에게 자기 출력을 검증시키지 않는다.)

설계 변경 (2026-08-25):
  측정값(대비·좌표·접힘선·겹침)은 지도에 넣지 않는다.
  스크린샷을 본 LLM은 대비 비율을 계산할 수 없고 y좌표를 픽셀로 못 읽는다.
  그럴듯한 숫자를 지어내고, 그 틀린 숫자는 금칙어 필터를 그냥 통과한다.
  이 수치들은 snapshot.py가 DOM/CSSOM에서 결정론적으로 계산하며, 매 스텝
  실시간으로 뽑히므로 상태가 변해도 낡지 않는다.

  지도  = 상태와 무관한 서술 (LLM)        <- layout, elements 이름
  스냅샷 = 상태에 의존하는 수치 (코드)     <- 대비, 좌표, 접힘선

  덕분에 지도에 없는 페이지에서 잃는 것은 서술 한 줄뿐이고,
  시각 정보는 그대로 다 들어온다.
"""
from __future__ import annotations

import json
import re

from . import config, discover
from .llm import Usage, chat_json
from .snapshot import take_snapshot

# ── 판단 표현 필터 ────────────────────────────────────────────────
# 사실/판단의 기준: 카메라로 찍어서 확인 가능한가.
# "겹친다"는 사실이고 "가린다"는 판단이다.
BANNED_WORDS = [
    "불편", "헷갈", "어렵", "이상", "작동하지", "안 됨", "안됨",
    "문제", "개선", "너무", "부족", "과하", "좋", "나쁘",
    "명확", "모호", "혼란", "직관", "불친절", "아쉽",
    "느리", "복잡", "번거", "실패", "오류로 보",
]

# "3개 이상", "16px 이상" 같은 수량 비교는 판단이 아니다. 검사 전에 걷어낸다.
_NUMERIC_ISANG = re.compile(r"\d+\s*(?:개|장|원|px|%|건|초|명|열|단계)?\s*이상")


def _scan(text: str) -> list[str]:
    cleaned = _NUMERIC_ISANG.sub("", text)
    return [w for w in BANNED_WORDS if w in cleaned]


# ── 언어 이탈 검사 ────────────────────────────────────────────────
# 금칙어 목록이 한국어 문자열이라, 모델이 중국어나 일본어로 새면 필터가
# 통째로 무력해진다. "布局不便" 은 판단이지만 BANNED_WORDS 에 걸리지 않는다.
# 프로바이더를 바꿀 때(Qwen 등) 이 구멍이 실제로 열린다.
_CJK = re.compile(r"[一-鿿぀-ヿ]")   # 한자·가나
_HANGUL = re.compile(r"[가-힣]")


def _lang_issues(text: str) -> list[str]:
    """한국어로 쓰였는지 본다. 상품명에 영어가 섞이는 것은 정상이므로
    영어는 막지 않고, 한자·가나만 잡는다."""
    t = (text or "").strip()
    if not t:
        return []
    out = []
    bad = _CJK.findall(t)
    if bad:
        out.append("한국어가 아닌 문자 %r" % "".join(sorted(set(bad))[:6]))
    # 문장인데 한글이 한 자도 없으면 통째로 영어/다른 언어로 쓴 것이다.
    if len(t) > 12 and not _HANGUL.search(t):
        out.append("한글이 없음")
    return out


def validate_page(page_entry: dict) -> list[str]:
    """LLM이 쓴 부분만 검사한다. 코드가 만든 값은 편들지 않으므로 제외."""
    issues = []
    path = page_entry.get("path", "?")
    for field in ("layout", "title"):
        value = str(page_entry.get(field) or "")
        for w in _scan(value):
            issues.append(f"{path}.{field}: 판단 표현 '{w}'")
        if field != "title":     # 제목은 사이트가 준 값이라 우리가 통제하지 않는다
            for msg in _lang_issues(value):
                issues.append(f"{path}.{field}: {msg}")
    for el in page_entry.get("elements") or []:
        blob = f"{el.get('name', '')} {el.get('where', '')} {el.get('type', '')}"
        for w in _scan(blob):
            issues.append(f"{path}.elements[{el.get('name', '?')}]: 판단 표현 '{w}'")
        # 요소 '이름'은 화면에 적힌 글자를 그대로 옮긴 것일 수 있어 언어 검사에서
        # 뺀다. 우리가 통제하는 것은 위치 서술(where)이다.
        for msg in _lang_issues(str(el.get("where") or "")):
            issues.append(f"{path}.elements[{el.get('name', '?')}]: {msg}")
    for st in page_entry.get("steps") or []:
        for w in _scan(json.dumps(st, ensure_ascii=False)):
            issues.append(f"{path}.steps[{st.get('n', '?')}]: 판단 표현 '{w}'")
    return issues


def validate_map(site_map: dict) -> list[str]:
    issues = []
    for p in site_map.get("pages", []):
        issues += validate_page(p)
    for w in _scan(str(site_map.get("structure") or "")):
        issues.append(f"structure: 판단 표현 '{w}'")
    return issues


# ── 프롬프트 ──────────────────────────────────────────────────────

SYSTEM = """당신은 웹사이트의 구조를 기록하는 조사원입니다.

[절대 규칙]
당신은 평가하지 않습니다. 관찰만 기록합니다.
다음 표현을 절대 사용하지 마세요:
- 불편하다, 헷갈린다, 찾기 어렵다, 이상하다
- 작동하지 않는다, 문제가 있다, 개선이 필요하다
- 너무 (길다/작다/많다), 부족하다, 과하다
- 좋다, 나쁘다, 명확하다, 모호하다, 복잡하다, 번거롭다

당신의 기준: "카메라로 찍어서 확인할 수 있는 사실인가?"
확인 가능하면 기록하고, 해석이 필요하면 쓰지 마세요.

[수치를 지어내지 마세요]
색 대비 비율, 픽셀 좌표, 요소 크기는 기록하지 않습니다.
그 값들은 별도의 계산 모듈이 정확하게 측정합니다.
당신은 눈으로 보이는 배치와 요소의 이름만 서술하세요.

반드시 한국어로 작성하세요."""

USER_TMPL = """아래는 '{title}' 페이지({path})의 스크린샷입니다.
위에서 아래로 스크롤하며 찍은 {n}장입니다.

[기록할 것]
1. layout — 화면이 어떻게 나뉘어 있는지 한두 문장. 예: "좌측 필터 영역, 우측 상품 그리드 3열"
2. elements — 조작 가능한 요소들. 각각 name(이름) / type(버튼·링크·입력·선택 등) / where(대략 어디에 있는지 말로)
3. steps — 이 페이지가 여러 단계로 된 절차의 일부라면 단계 번호와 이름. 아니면 null

[출력 형식 — JSON만, 다른 말 금지]
{{
  "layout": "...",
  "elements": [{{"name": "...", "type": "...", "where": "..."}}],
  "steps": null
}}"""


def mock_page(path: str, title: str) -> dict:
    """--mock 용. LLM 없이 파이프라인 전체를 돌려보기 위한 자리표시자."""
    return {
        "layout": f"({path} 자리표시자) 상단 헤더, 중앙 본문, 하단 푸터로 구성",
        "elements": [{"name": "헤더 로고", "type": "링크", "where": "좌측 상단"}],
        "steps": None,
    }


# ── 페이지 1장 답사 ────────────────────────────────────────────────

async def shoot(page, max_shots: int = config.SURVEY_SHOTS_PER_PAGE) -> list[bytes]:
    """뷰포트 높이만큼 내려가며 최대 N장. 전체 페이지 1장보다 세로로 긴
    페이지에서 요소가 뭉개지지 않는다."""
    h = config.VIEWPORT["height"]
    total = await page.evaluate("document.documentElement.scrollHeight")
    shots = []
    for i in range(max_shots):
        y = i * h
        if i and y >= total:
            break
        await page.evaluate(f"window.scrollTo(0, {y})")
        shots.append(await page.screenshot(type="png"))
    await page.evaluate("window.scrollTo(0, 0)")
    return shots


async def survey_page(page, target: dict, root: str, *, client, model: str,
                      shots_dir: str | None = None,
                      usage: Usage, mock: bool, edges: dict) -> tuple[dict, dict]:
    """반환: (지도 항목, 참고용 측정값)

    측정값은 지도에 넣지 않는다. survey_meta에만 남겨 사람이 눈으로 보고
    clean/buggy를 비교하는 용도로 쓴다. 프롬프트에는 절대 들어가지 않는다.
    """
    url = target["url"]
    # 먼저 화면이 뜨는 것까지만 기다리고, 조용해지는 것은 **되면 좋고** 로 둔다.
    #
    # networkidle 을 필수로 걸면 스스로 계속 무언가를 불러오는 사이트에서
    # 영영 끝나지 않는다 — 나무위키가 그랬고, 답사가 첫 페이지에서 시간 초과로
    # 통째로 죽었다. 우리 테스트베드는 정적 파일이라 티가 안 났던 문제다.
    await page.goto(url, wait_until="domcontentloaded",
                    timeout=config.STEP_TIMEOUT_MS * 3)
    try:
        await page.wait_for_load_state("networkidle",
                                       timeout=config.STEP_TIMEOUT_MS)
    except Exception:  # noqa: BLE001
        # 안 조용해지는 사이트. 이미지가 자리를 잡을 짬만 주고 진행한다.
        await page.wait_for_timeout(1500)
    path = discover.rel_path(url, root)
    title = await page.title()

    snap = await take_snapshot(page)   # 코드가 계산하는 정확한 수치

    if mock:
        body = mock_page(path, title)
    else:
        shots = await shoot(page)
        # 모델에 보낸 그림을 그대로 남긴다. 보내고 버리면 "무엇을 보고 이
        # 설명서를 썼는가"를 나중에 아무도 확인할 수 없다. 페르소나는 글로만
        # 움직이므로 이 파이프라인에서 그림이 남는 곳은 여기뿐이다.
        if shots_dir:
            import os as _os
            _os.makedirs(shots_dir, exist_ok=True)
            # 한글 경로는 퍼센트 인코딩으로 온다. 그대로 파일명에 쓰면
            # 'EC_9C_84_ED_82_A4...' 가 되어 사람이 못 알아본다.
            from urllib.parse import unquote as _unq
            safe = "".join(c if (c.isalnum() or c in "-_.") else "_"
                           for c in _unq(path))[:60]
            for i, raw in enumerate(shots, 1):
                with open(_os.path.join(shots_dir, "%s__%d.png" % (safe.strip("_") or "page", i)),
                          "wb") as f:
                    f.write(raw)
        body = chat_json(
            client,
            model=model,
            system=SYSTEM,
            user=USER_TMPL.format(title=title, path=path, n=len(shots)),
            images=shots,
            temperature=config.TEMP_SURVEY,
            usage=usage,
        )

    entry = {
        "path": path,
        "template": discover.template_key(url),
        "title": title,
        "found_by": target["found_by"],
        "layout": body.get("layout"),
        "elements": body.get("elements") or [],
        # links_to / steps 는 지도에 남기되 페르소나 슬라이스에는 넣지 않는다.
        # 처음 온 사람이 결제 단계 수를 알 리 없다.
        "links_to": edges.get(discover.template_key(url), []),
        "steps": body.get("steps"),
    }
    measurements = {
        "path": path,
        "element_count": len(snap["elements"]),
        "horizontal_scroll": snap["horizontal_scroll"],
        "body_contrast": snap["body_contrast"],
        "body_font_size": snap["body_font_size"],
        "below_fold": sum(1 for e in snap["elements"] if e["below_fold"]),
        "occluded": sum(1 for e in snap["elements"] if e["occluded"]),
        # disabled 컨트롤은 WCAG 면제 대상이라 세지 않는다 (snapshot._flag_str와 동일 규칙)
        "low_contrast": sum(1 for e in snap["elements"]
                            if (e.get("contrast") or 99) < 3.0
                            and not e.get("disabled_attr")),
        "keyboard_unreachable": sum(1 for e in snap["elements"]
                                    if not e["keyboard_reachable"]),
        "missing_alt": snap.get("images", {}).get("missing_alt"),
    }
    return entry, measurements


# ── 지도 슬라이스 (탐색 단계에서 사용) ──────────────────────────────

def get_map_slice(site_map: dict, current_url: str, root: str) -> dict | None:
    """현재 페이지 부분만 돌려준다. 전체를 넘기면 처음 온 사람이 사이트
    전체 구조를 아는 비현실적 최적화가 된다.

    links_to / steps 는 의도적으로 뺀다. 가보지 않은 곳을 미리 알면 안 된다.
    measurements 는 애초에 지도에 없다 — 실시간 스냅샷에서 온다.
    """
    key = discover.template_key(current_url)
    for p in site_map.get("pages", []):
        if p["template"] == key:
            return {"layout": p.get("layout"), "elements": p.get("elements") or []}
    return None   # 지도에 없는 페이지 = map_miss
