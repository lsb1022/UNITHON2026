"""탐색 루프의 머리 — 무엇을 보여주고, 무엇을 돌려받고, 어떻게 실행하는가.

세 가지를 여기서 못박는다.

1. **탐색 중에는 이슈 분석을 시키지 않는다.** "문제점을 알려줘"라고 물으면
   모델은 반드시 목록을 만들어낸다. 멀쩡한 화면에서도 만든다. 그건 오탐률
   (차별점 ①)을 통째로 무너뜨린다. 여기서 받는 것은 **생각과 행동 하나**뿐이고,
   결함 판정은 실행이 다 끝난 뒤 완전히 별개 단계에서 한다.

2. **좌표로 조작하지 않는다.** 스냅샷이 요소마다 붙여둔 이름(data-agent-id)으로
   지목한다. 좌표로 누르면 화면이 조금만 바뀌어도 깨지고, 깨진 클릭이
   '사용자가 못 눌렀다'로 기록되어 결함처럼 보인다.

3. **최근 3스텝만 보여준다.** 전체 이력을 누적하면 30스텝째에 프롬프트가
   수십 배로 불어나고, 스텝당 비용이 스텝 수에 비례해 커진다.
"""
from __future__ import annotations

import asyncio
import json
import re

from . import config
from .snapshot import render_for_prompt

# 목록에 없어도 항상 허용되는 제어 행동. 끝내겠다는 의사 표시는 막을 수 없다.
CONTROL = ("done", "give_up")
# 러너가 실제로 수행할 수 있는 행동 전부.
KNOWN = ("click", "type", "select", "scroll", "back", "wait", "goto") + CONTROL


SYSTEM = """당신은 지금 어떤 온라인 쇼핑몰을 쓰고 있는 사람입니다.

[당신이 아는 것]
- 지금 화면에 보이는 것뿐입니다. 사이트 전체 구조는 모릅니다.
- 당신은 테스터가 아닙니다. 문제점을 목록으로 만들지 마세요.
  그냥 목표를 이루려고 행동하면 됩니다.

[생각]
- thought 에는 지금 무엇을 하려는지, 왜 그렇게 하는지 한두 문장을 씁니다.
- 화면에서 뭔가 안 보이거나 눌리지 않으면 그 느낌을 그대로 쓰세요.
  단, 그것을 '결함 보고'로 정리하지는 마세요.

[행동]
- 한 번에 하나만 합니다.
- 요소는 반드시 목록에 있는 이름(link_3, button_1 …)으로 지목합니다.
- 목표를 이뤘으면 done, 더는 못 하겠으면 give_up 을 쓰세요.
  못 하겠으면 참지 말고 give_up 을 쓰는 편이 낫습니다.

반드시 한국어로 작성하세요.

[출력 형식 — JSON만, 다른 말 금지]
{"thought": "...", "action": {"type": "click", "target": "link_3"}}
{"thought": "...", "action": {"type": "type", "target": "input_2", "value": "홍길동"}}
{"thought": "...", "action": {"type": "scroll"}}
{"thought": "...", "action": {"type": "give_up"}}"""


def history_block(steps: list[dict], window: int = config.HISTORY_WINDOW) -> str:
    """최근 몇 스텝만. 전체 누적 금지."""
    if not steps:
        return "(아직 아무것도 하지 않았습니다)"
    out = []
    for s in steps[-window:]:
        act = s["action"]
        tgt = (" " + act["target"]) if act.get("target") else ""
        line = "%d. %s → %s%s" % (s["step"], s["thought"][:60], act["type"], tgt)
        note = (s.get("outcome") or {}).get("note")
        if note:
            line += "  (%s)" % note
        if s.get("blocked_action"):
            line += "  (그 행동은 할 수 없었습니다)"
        out.append(line)
    return "\n".join(out)


def build_user(persona: dict, snap: dict, steps: list[dict],
               map_slice: dict | None) -> str:
    parts = [persona["prompt"], ""]

    # 지도 슬라이스는 현재 페이지 부분만. 가보지 않은 곳을 미리 알면 안 된다.
    if map_slice:
        names = ", ".join(e.get("name", "?") for e in (map_slice.get("elements") or [])[:10])
        parts += ["[이 화면에 대해 아는 것]",
                  "배치: %s" % map_slice.get("layout"),
                  "요소: %s" % names, ""]

    parts += ["[지금 화면]", render_for_prompt(snap), "",
              "[방금 한 일]", history_block(steps), "",
              "[할 수 있는 행동] %s" % ", ".join(persona["allowed_actions"] + list(CONTROL)),
              "",
              "무엇을 하시겠습니까? JSON 하나만 출력하세요."]
    return "\n".join(parts)


def decide(client, persona: dict, snap: dict, steps: list[dict],
           map_slice: dict | None, *, model: str, usage, mock: bool) -> dict:
    """생각 + 행동 하나를 받아온다."""
    if mock:
        return mock_decide(persona, snap, steps)

    from .llm import chat_json

    body = chat_json(
        client,
        model=model,
        system=SYSTEM,
        user=build_user(persona, snap, steps, map_slice),
        temperature=config.TEMP_EXPLORE,
        usage=usage,
    )
    action = body.get("action") or {}
    if isinstance(action, str):          # {"action": "scroll"} 로 오는 경우
        action = {"type": action}
    action.setdefault("type", "scroll")
    return {"thought": str(body.get("thought") or "").strip() or "(생각 없음)",
            "action": action}


# ── 모의 정책 (--mock) ────────────────────────────────────────────
# LLM 없이 루프·기록·저장이 도는지 확인하기 위한 것이다. 똑똑할 필요가 없다.
# 다만 '아무거나 누르는' 것으로는 결제까지 못 가서 저장 경로가 검증되지 않으므로,
# 구매 흐름의 낱말을 우선해 앞으로 나아가게만 해둔다.
_FORWARD = ("담기", "장바구니", "주문", "결제", "구매", "다음", "계속", "완료")


_CLOSE = ("닫기", "close", "×", "✕", "x")


def mock_decide(persona: dict, snap: dict, steps: list[dict]) -> dict:
    # 요소 이름(link_1 …)은 페이지마다 새로 붙는다. URL과 묶지 않으면 다른
    # 화면의 link_1 을 '이미 눌러봤다'고 착각해 모의 실행이 앞으로 못 간다.
    used = {((s.get("outcome") or {}).get("url_after"), s["action"].get("target"))
            for s in steps}
    els = [e for e in snap["elements"]
           if (snap["url"], e["id"]) not in used and not e["occluded"]]

    # 화면 절반 이상이 가려졌으면 먼저 치운다. 실제 사람이 하는 일이고,
    # 이걸 안 하면 모의 실행이 팝업 앞에서 맴돌다 끝나 저장 경로가 덜 검증된다.
    blocked = sum(1 for e in snap["elements"] if e["occluded"])
    if blocked and blocked * 2 >= len(snap["elements"]):
        for e in els:
            if any(w in (e["text"] or "").lower() for w in _CLOSE):
                return {"thought": "가리고 있는 것을 먼저 닫겠습니다.",
                        "action": {"type": "click", "target": e["id"]}}

    for e in els:
        if any(w in (e["text"] or "") for w in _FORWARD):
            return {"thought": "'%s' 를 눌러 다음으로 가보겠습니다." % e["text"],
                    "action": {"type": "click", "target": e["id"]}}

    if "complete" in snap["url"]:
        return {"thought": "주문이 끝난 것 같습니다.", "action": {"type": "done"}}

    links = [e for e in els if e["tag"] == "a" and not e["below_fold"]]
    if links:
        return {"thought": "'%s' 로 가보겠습니다." % (links[0]["text"] or links[0]["id"]),
                "action": {"type": "click", "target": links[0]["id"]}}

    if len(steps) >= 3 and all(s["action"]["type"] == "scroll" for s in steps[-3:]):
        return {"thought": "더 볼 것이 없습니다.", "action": {"type": "give_up"}}
    return {"thought": "아래를 더 보겠습니다.", "action": {"type": "scroll"}}


# ── 행동 실행 ─────────────────────────────────────────────────────

async def execute(page, action: dict, root: str) -> dict:
    """행동 하나를 수행하고 결과를 돌려준다. 예외를 밖으로 내보내지 않는다.

    실패도 결과다. '눌렀는데 아무 일도 안 일어났다'는 마찰의 기록이지
    러너의 오류가 아니다.
    """
    t = action.get("type")
    target = action.get("target")
    value = action.get("value")
    sel = '[data-agent-id="%s"]' % target if target else None
    before = page.url
    note = ""

    try:
        if t == "click":
            if not sel:
                return {"changed": False, "note": "지목한 요소가 없습니다"}
            await page.click(sel, timeout=config.STEP_TIMEOUT_MS)
        elif t == "type":
            if not sel:
                return {"changed": False, "note": "지목한 요소가 없습니다"}
            await page.fill(sel, str(value or ""), timeout=config.STEP_TIMEOUT_MS)
        elif t == "select":
            try:
                await page.select_option(sel, str(value or ""), timeout=config.STEP_TIMEOUT_MS)
            except Exception:  # noqa: BLE001 - value 가 아니라 보이는 라벨로 골랐을 때
                await page.select_option(sel, label=str(value or ""),
                                         timeout=config.STEP_TIMEOUT_MS)
        elif t == "scroll":
            await page.evaluate("window.scrollBy(0, Math.round(window.innerHeight * 0.8))")
        elif t == "back":
            await page.go_back(timeout=config.STEP_TIMEOUT_MS)
        elif t == "wait":
            await asyncio.sleep(2)
        elif t == "goto":
            dest = str(value or target or "")
            url = dest if dest.startswith("http") else root.rstrip("/") + "/" + dest.lstrip("/")
            if not url.startswith(root):
                return {"changed": False, "note": "사이트 밖 주소라 가지 않았습니다"}
            await page.goto(url, timeout=config.STEP_TIMEOUT_MS)
        else:
            return {"changed": False, "note": "알 수 없는 행동 %r" % t}
    except Exception as e:  # noqa: BLE001 - 클릭 실패는 마찰이지 오류가 아니다
        note = _short_error(e)

    # 페이지가 반응할 짬. networkidle 은 자동 팝업 타이머 때문에 오래 걸릴 수 있어 쓰지 않는다.
    try:
        await page.wait_for_load_state("domcontentloaded", timeout=3000)
    except Exception:  # noqa: BLE001
        pass

    after = page.url
    return {"url_after": after, "changed": after != before,
            "note": note or ("" if after != before else "화면이 바뀌지 않았습니다")}


_ERR = re.compile(r"^\s*([^\n]{0,120})")


def _short_error(e: Exception) -> str:
    """Playwright 예외는 수십 줄이다. 첫 줄만 남긴다."""
    m = _ERR.match(str(e) or "")
    head = (m.group(1) if m else "").strip()
    if "Timeout" in head:
        return "눌리지 않았습니다 (시간 초과)"
    return head[:120] or e.__class__.__name__


def check_allowed(action: dict, persona: dict) -> dict | None:
    """허용 목록 밖이면 그 행동을 돌려준다 (러너가 blocked_action 으로 기록).

    목록은 장식이 아니라 실제로 강제된다. 서툰 사람이 주소창으로 결제
    페이지에 바로 가버리면 길찾기 마찰이 통째로 측정에서 사라진다.
    """
    t = action.get("type")
    if t in CONTROL:
        return None
    if t not in persona["allowed_actions"]:
        return dict(action)
    return None


def _key(s: dict) -> tuple:
    return ((s.get("outcome") or {}).get("url_after"),
            s["action"]["type"], s["action"].get("target"))


def loop_detected(steps: list[dict], url: str) -> bool:
    """맴돌고 있는지. 두 가지를 본다.

    ① 제자리: 같은 화면에서 같은 행동을 연속 반복
    ② 왕복: A→B→A→B 처럼 두 화면을 오가며 같은 것만 누름

    ②가 없으면 왕복하는 사람은 30스텝을 다 태운다. 스텝마다 LLM 호출이므로
    이건 곧 토큰이다. 그리고 종료 사유가 `max_steps` 로 찍혀서 '스텝이 모자랐다'와
    '길을 잃었다'가 구분되지 않는다.
    """
    if len(steps) < config.LOOP_THRESHOLD:
        return False

    recent = steps[-config.LOOP_THRESHOLD:]
    same_url = all((s.get("outcome") or {}).get("url_after") == url for s in recent)
    if same_url and len({(s["action"]["type"], s["action"].get("target"))
                         for s in recent}) == 1:
        return True

    window = steps[-(config.LOOP_THRESHOLD * 2):]
    if len(window) < config.LOOP_THRESHOLD * 2:
        return False
    counts = {}
    for s in window:
        k = _key(s)
        counts[k] = counts.get(k, 0) + 1
    return max(counts.values()) >= config.LOOP_THRESHOLD
