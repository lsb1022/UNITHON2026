"""탐색 루프의 머리 — 무엇을 보여주고, 무엇을 돌려받고, 어떻게 실행하는가.

세 가지를 여기서 못박는다.

1. **탐색 중에는 이슈 분석을 시키지 않는다.** "문제점을 알려줘"라고 물으면
   모델은 반드시 목록을 만들어낸다. 멀쩡한 화면에서도 만든다. 그건 오탐률
   (차별점 ①)을 통째로 무너뜨린다. 여기서 받는 것은 **생각과 행동 하나**뿐이고,
   결함 판정은 실행이 다 끝난 뒤 완전히 별개 단계에서 한다.

2. **좌표로 조작하지 않는다.** 스냅샷이 요소마다 붙여둔 이름(data-agent-id)으로
   지목한다. 좌표로 누르면 화면이 조금만 바뀌어도 깨지고, 깨진 클릭이
   '사용자가 못 눌렀다'로 기록되어 결함처럼 보인다.

3. **최근 몇 스텝만 보여준다 (config.HISTORY_WINDOW).** 전체 이력을 누적하면 30스텝째에 프롬프트가
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
- [radio] [checkbox] 는 click 으로 고릅니다. type 은 글자를 넣는 칸에만 씁니다.
- 같은 행동이 실패하면 그대로 반복하지 말고 다른 방법을 쓰세요.
- 목표를 이뤘으면 done, 더는 못 하겠으면 give_up 을 쓰세요.
  못 하겠으면 참지 말고 give_up 을 쓰는 편이 낫습니다.

반드시 한국어로 작성하세요.

[출력 형식 — JSON만, 다른 말 금지]
{"thought": "...", "action": {"type": "click", "target": "link_3"}}
{"thought": "...", "action": {"type": "type", "target": "input_2", "value": "홍길동"}}
{"thought": "...", "action": {"type": "scroll"}}
{"thought": "...", "action": {"type": "give_up"}}"""


def _one_line(s: dict) -> str:
    act = s["action"]
    tgt = (" " + act["target"]) if act.get("target") else ""
    line = "%d. %s → %s%s" % (s["step"], s["thought"][:60], act["type"], tgt)
    note = (s.get("outcome") or {}).get("note")
    if note:
        line += "  (%s)" % note
    if s.get("blocked_action"):
        line += "  (그 행동은 할 수 없었습니다)"
    return line


def history_block(steps: list[dict], window: int = config.HISTORY_WINDOW,
                  head: int = config.HISTORY_HEAD) -> str:
    """맨 앞 몇 스텝 + 최근 몇 스텝. 가운데는 접는다.

    창을 뒤에서만 자르면 **목표를 이룬 결정적 행동이 먼저 밀려난다.**
    실측: "담아둔 상품의 수량을 2개로 바꿔 주문한다" 목표에서 4명 전원이
    1스텝에 수량 변경을 성공해놓고, 결제 폼을 채우는 6스텝 동안 그 사실이
    창 밖으로 나가 9스텝째에 "수량을 바꾸러 장바구니로 돌아가겠다"며 맴돌았다.

    창을 키우면 비용만 커지고 긴 실행에서 같은 일이 다시 난다. 앞을 남기는
    편이 싸고 정확하다 — 시작 부분은 대개 목표에 직결된 행동이다.
    """
    if not steps:
        return "(아직 아무것도 하지 않았습니다)"
    if len(steps) <= window + head:
        return "\n".join(_one_line(s) for s in steps)

    front = [_one_line(s) for s in steps[:head]]
    back = [_one_line(s) for s in steps[-window:]]
    skipped = len(steps) - head - window
    return "\n".join(front + ["… (%d스텝 생략)" % skipped] + back)


def build_user(persona: dict, snap: dict, steps: list[dict],
               map_slice: dict | None) -> str:
    parts = [persona["prompt"], ""]

    # 지도 슬라이스는 현재 페이지 부분만. 가보지 않은 곳을 미리 알면 안 된다.
    if map_slice:
        names = ", ".join(e.get("name", "?") for e in (map_slice.get("elements") or [])[:10])
        parts += ["[이 화면에 대해 아는 것]",
                  "배치: %s" % map_slice.get("layout"),
                  "요소: %s" % names, ""]

    parts += ["[지금 화면]", render_for_prompt(snap, config.PROMPT_ELEMENT_LIMIT), "",
              "[방금 한 일]", history_block(steps), "",
              "[할 수 있는 행동] %s" % ", ".join(persona["allowed_actions"] + list(CONTROL)),
              "",
              "무엇을 하시겠습니까? JSON 하나만 출력하세요."]
    return "\n".join(parts)


def decide(client, persona: dict, snap: dict, steps: list[dict],
           map_slice: dict | None, *, models: list[str], usage, mock: bool) -> dict:
    """생각 + 행동 하나를 받아온다.

    모델을 목록으로 받는다. 100명 x 30스텝을 달리는 동안 한 모델이 과부하(503)
    나는 일이 실제로 있었다. 같은 등급의 다른 모델로 넘어가면 실행이 산다.
    """
    if mock:
        return mock_decide(persona, snap, steps)

    from .llm import chat_json_any

    body = chat_json_any(
        client,
        models=models,
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

CLICKABLE_INPUTS = ("radio", "checkbox")

# 행동 전후로 화면이 실제로 어떻게 달라졌는지 재는 데 쓴다.
# URL 만 비교하면 '장바구니에 담기', '폼 입력', '체크박스 선택'이 전부
# "아무 일도 안 일어났다"로 보고된다. 그러면 페르소나가 자기 행동이 먹혔는지
# 알 수 없어 의심하고, 되돌아가서 다시 하고, 스텝을 다 태운다.
# (실제로 겪음: clean 사이트에서 P001 이 결제 폼을 두 번 채우고 30스텝을 소진했다.)
_STATE_JS = """() => ({
  url: location.href,
  n: document.querySelectorAll(
       "a[href],button,input,select,textarea,summary,[role=button]").length,
  y: Math.round(window.scrollY),
  lines: (document.body ? document.body.innerText : "")
           .split("\\n").map(s => s.trim()).filter(Boolean),
})"""


# '처리 중' 표시가 떠 있으면 화면이 넘어갈 때까지 기다린다.
# clean 결제 화면은 버튼을 누르고 1.2초 뒤에 완료 화면으로 넘어가는데, 그 사이에
# 스냅샷을 찍으면 페르소나는 "결제 처리 중이라는 문구만 뜨고 아무 일도 없다"고
# 판단해 포기한다 (실제로 P012 가 13스텝에서 그렇게 끝났다). 사람은 기다린다.
_BUSY_JS = """() => {
  if (document.querySelector('[aria-busy="true"],.spinner,.loading,.is-loading'
                             + ',[class*="progress"]')) return true;
  const t = (document.body ? document.body.innerText : "");
  return /처리\\s*중|진행\\s*중|로딩|잠시만|Processing|Loading/i.test(t);
}"""


async def _settle(page, before_url: str, budget_ms: int = 6000) -> None:
    """처리 중 표시가 있는 동안만 잠깐 더 기다린다. 없으면 즉시 돌아간다."""
    waited = 0
    step = 400
    while waited < budget_ms:
        try:
            if page.url != before_url or not await page.evaluate(_BUSY_JS):
                return
        except Exception:  # noqa: BLE001 - 이동 중이면 다음 회차에 다시 본다
            return
        await asyncio.sleep(step / 1000)
        waited += step


async def _state(page) -> dict:
    try:
        return await page.evaluate(_STATE_JS)
    except Exception:  # noqa: BLE001 - 이동 중이면 못 읽는다. 없으면 없는 대로 간다
        return {}


def _diff_note(before: dict, after: dict) -> str:
    """무엇이 달라졌는지 사람 말로. 없으면 빈 문자열."""
    if not before or not after:
        return ""
    # 새로 나타난 글자가 가장 값진 신호다. 토스트("장바구니에 담았습니다"),
    # 오류 문구("필수 항목입니다") 가 여기에 잡힌다.
    fresh = [t for t in after.get("lines", []) if t not in set(before.get("lines", []))]
    fresh = [t for t in fresh if len(t) > 1][:2]
    if fresh:
        return "새로 나타난 글자: " + " / ".join(t[:40] for t in fresh)
    if after.get("n") != before.get("n"):
        return "화면 내용이 바뀌었습니다 (조작 가능한 요소 %d개 → %d개)" % (
            before.get("n", 0), after.get("n", 0))
    # 스크롤 위치 변화는 신호가 아니다. Playwright 가 요소를 보이게 하려고
    # 스스로 스크롤하므로, 이걸 '변화'로 치면 체크박스 선택 같은 진짜 결과를
    # 가린다. 스크롤은 사용자가 스크롤을 요청했을 때만 execute 가 따로 알린다.
    return ""


async def execute(page, action: dict, root: str, element: dict | None = None) -> dict:
    """행동 하나를 수행하고 결과를 돌려준다. 예외를 밖으로 내보내지 않는다.

    실패도 결과다. '눌렀는데 아무 일도 안 일어났다'는 마찰의 기록이지
    러너의 오류가 아니다.
    """
    t = action.get("type")
    target = action.get("target")
    value = action.get("value")
    sel = '[data-agent-id="%s"]' % target if target else None
    before = page.url
    before_state = await _state(page)
    note = ""

    # 라디오·체크박스에 글자를 넣으려 하면 Playwright 가 거부한다. 이건 사이트의
    # 마찰이 아니라 지목 방식의 불일치이므로 클릭으로 바꿔 수행하고 기록에 남긴다.
    # (실제로 겪음: 모델이 라디오에 type 을 5번 반복하다 답사가 끝났다.)
    if t == "type" and element and element.get("input_type") in CLICKABLE_INPUTS:
        t = "click"
        note = "%s 라서 입력 대신 선택으로 처리" % element["input_type"]

    try:
        # 값 없는 입력은 수행하지 않는다. fill("") 은 성공하면서 칸을 지우기 때문에
        # '아무 일도 안 일어났다'만 돌아오고, 모델은 자기가 헛일을 하는지 모른다.
        # (실제로 겪음: 값 없는 type 을 12번 반복하다 답사가 끝났다.)
        if t == "type" and not str(value or "").strip():
            return {"url_after": before, "changed": False,
                    "note": "입력할 값이 없어 실행하지 않았습니다. value 를 함께 주세요"}

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
        # '눌리지 않았다'만 남기면 왜 안 눌렸는지 모른다. 그 자리를 실제로
        # 덮고 있는 것이 무엇인지 브라우저에 물어 기록한다. 이것이야말로
        # 스크린샷 대신 쓰는 계산된 시각 정보다.
        if t in ("click", "type", "select") and sel:
            blocker = await _who_blocks(page, sel)
            if blocker:
                note = "%s 이(가) 덮고 있어 눌리지 않았습니다" % blocker

    # 페이지가 반응할 짬. networkidle 은 자동 팝업 타이머 때문에 오래 걸릴 수 있어 쓰지 않는다.
    try:
        await page.wait_for_load_state("domcontentloaded", timeout=3000)
    except Exception:  # noqa: BLE001
        pass
    # '처리 중'이 떠 있으면 결과가 나올 때까지만 더 기다린다. 사람이 하는 일이다.
    await _settle(page, before)

    after = page.url
    moved = after != before
    if moved:
        # 화면이 넘어갔으면 그 자체가 가장 큰 변화다. 더 볼 것 없다.
        return {"url_after": after, "changed": True, "note": note}

    # 같은 화면에 머물렀다면 '정말 아무 일도 없었는지' 확인한다.
    after_state = await _state(page)
    detail = _diff_note(before_state, after_state)

    # 입력은 값이 들어갔는지 직접 읽는다. 가장 확실한 확인이다.
    if t == "type" and sel and not note:
        try:
            got = await page.input_value(sel, timeout=2000)
            if got:
                detail = '입력값이 "%s" 로 들어갔습니다' % got[:30]
        except Exception:  # noqa: BLE001 - 읽을 수 없으면 다른 신호를 쓴다
            pass
    # 체크박스·라디오는 선택 상태를 읽는다.
    if t == "click" and sel and not detail:
        try:
            if await page.is_checked(sel, timeout=1000):
                detail = "선택됐습니다"
        except Exception:  # noqa: BLE001 - 체크 대상이 아니면 그냥 넘어간다
            pass

    # 스크롤은 사용자가 요청했을 때만 결과로 말한다.
    if t == "scroll" and not detail:
        dy = (after_state.get("y", 0) - before_state.get("y", 0))
        detail = ("%d픽셀 내려갔습니다" % dy) if dy else "더 내려갈 곳이 없습니다"

    parts = [x for x in (note, detail) if x]
    return {"url_after": after, "changed": bool(detail),
            "note": " / ".join(parts) if parts else "아무 변화가 없었습니다"}


_ERR = re.compile(r"^\s*([^\n]{0,120})")


_BLOCKER_JS = """(sel) => {
  const el = document.querySelector(sel);
  if (!el) return "";
  const r = el.getBoundingClientRect();
  const hit = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);
  if (!hit || hit === el || el.contains(hit) || hit.contains(el)) return "";
  const box = hit.getBoundingClientRect();
  const cls = (typeof hit.className === "string" && hit.className.trim())
      ? "." + hit.className.trim().split(/\\s+/)[0] : "";
  const full = box.width >= innerWidth * 0.9 && box.height >= innerHeight * 0.9;
  return hit.tagName.toLowerCase() + cls +
      (full ? "(화면 전체를 덮는 층)"
            : "(" + Math.round(box.width) + "x" + Math.round(box.height) + ")");
}"""


async def _who_blocks(page, sel: str) -> str:
    """지목한 요소의 중심점을 실제로 차지하고 있는 것을 찾는다.

    스냅샷의 가림 여부는 '그때' 값이라 낡을 수 있다. LLM 이 생각하는
    10~20초 사이에 자동 팝업이 뜨면, 기록에는 '가려짐 0'인데 클릭은 실패하는
    모순이 남는다 (실제로 P003 에서 그렇게 남았다). 실패한 그 순간에 다시
    물어야 기록과 현실이 맞는다.
    """
    try:
        return await page.evaluate(_BLOCKER_JS, sel)
    except Exception:  # noqa: BLE001 - 진단이 실패해도 본 흐름은 계속된다
        return ""


def _short_error(e: Exception) -> str:
    """Playwright 예외는 수십 줄이다. 첫 줄만 남긴다."""
    m = _ERR.match(str(e) or "")
    head = (m.group(1) if m else "").strip()
    if "Timeout" in head:
        return "눌리지 않았습니다 (시간 초과)"
    return head[:120] or e.__class__.__name__


def check_allowed(action: dict, persona: dict,
                  element: dict | None = None) -> dict | None:
    """허용 목록 밖이면 그 행동을 돌려준다 (러너가 blocked_action 으로 기록).

    목록은 장식이 아니라 실제로 강제된다. 문장만 주면 모델이 무시한다.
    서툰 사람이 주소창으로 결제 페이지에 바로 가버리면 길찾기 마찰이
    통째로 측정에서 사라진다. 검색도 같은 이유로 막는다 — 검색창에
    상품명을 치는 것은 '길을 찾은 것'이 아니라 길찾기를 건너뛴 것이다.
    """
    t = action.get("type")
    if t in CONTROL:
        return None
    if t not in persona["allowed_actions"]:
        return dict(action)
    if (t == "type" and not persona.get("search_allowed", True)
            and element and element.get("input_type") == "search"):
        return dict(action, reason="검색은 이 사람의 숙련도에서 허용되지 않습니다")
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
