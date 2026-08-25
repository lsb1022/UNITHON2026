"""미션(목표) 검증 — 규칙으로 먼저 거르고, 나머지를 모델에게 묻는다.

**왜 두 겹인가.**

규칙으로 잡히는 것은 규칙으로 잡는다. '불편하다', '오류' 같은 판단 표현이
목표에 들어가면 100명 전원이 그 결함을 찾으러 가고, 적중률이 '우리가 미리
알려준 답을 세는 값'이 되어버린다. 이건 낱말만 보면 확실히 알 수 있으므로
모델에게 물을 이유가 없다 — 빠르고 공짜고 결과가 흔들리지 않는다.

모델이 필요한 것은 그다음이다. "이 사이트에서 실제로 할 수 있는 일인가",
"성공을 무엇으로 판정할 것인가"는 낱말 검사로 안 된다.

**성공 기준을 모델에게 시키는 이유.** 지금 성공은 페르소나가 스스로 done 을
외치면 성립한다. 그러면 잘못 외쳐도 성공으로 남는다. 코드가 확인할 수 있는
조건(도착 주소 / 화면에 보이는 글자)을 미리 받아두면 나중에 대조할 수 있다.
그 조건은 **페르소나에게 절대 보여주지 않는다** — 답을 쥐여주는 셈이 된다.
"""
from __future__ import annotations

import json

from . import config
from . import survey as SV

# 목표에 들어가면 안 되는 판단 표현. 규칙으로 확실히 잡히는 것들.
JUDGEMENT_HINT = ("무엇을 하려는지만 적어주세요. "
                  "예) 코튼 셔츠를 장바구니에 담아 주문까지 마친다")

SYSTEM = """당신은 UX 테스트의 미션 문장을 검토하는 사람입니다.

미션은 'AI 페르소나가 사이트에서 수행할 일 하나'입니다.

[좋은 미션]
- 할 일이 하나이고 구체적입니다.
- 사이트를 안 봐도 무슨 뜻인지 압니다.
- 끝났는지 아닌지 판정할 수 있습니다.

[나쁜 미션]
- 결함을 미리 알려줍니다 ("장바구니가 불편한지 확인해줘")
- 할 일이 여러 개입니다
- 너무 막연합니다 ("사이트를 둘러본다")

[성공 기준]
코드가 확인할 수 있는 조건으로 씁니다. 둘 중 하나 이상을 채우세요.
- url_contains: 이 문자열이 주소에 들어가면 도착한 것
- text_contains: 이 문자열이 화면에 보이면 확인한 것
확신할 수 없으면 빈 값으로 두세요. 지어내지 마세요.

[출력 — JSON만]
{"ok": true, "reason": "", "criteria": "사람이 읽을 한 문장",
 "check": {"url_contains": "", "text_contains": ""},
 "suggestion": ""}
{"ok": false, "reason": "왜 안 되는지 한 문장", "criteria": "",
 "check": {}, "suggestion": "이렇게 바꾸면 됩니다"}

반드시 한국어로 작성하세요."""


def rule_issues(goal: str) -> list[dict]:
    """모델을 부르기 전에 규칙으로 잡히는 것들."""
    g = (goal or "").strip()
    out: list[dict] = []
    if not g:
        return [{"kind": "empty", "message": "미션을 적어주세요.", "fix": JUDGEMENT_HINT}]
    if len(g) > 60:
        out.append({"kind": "length",
                    "message": "%d자입니다. 60자 이내로 줄여주세요." % len(g),
                    "fix": "페르소나마다 스텝마다 다시 보내는 문장이라 길면 값이 비쌉니다."})
    for w in SV._scan(g):
        out.append({"kind": "judgement",
                    "message": '"%s" 는 결함을 미리 알려주는 표현입니다.' % w,
                    "fix": JUDGEMENT_HINT})
    for msg in SV._lang_issues(g):
        out.append({"kind": "language", "message": msg, "fix": "한국어로 적어주세요."})
    return out


def analyze(goal: str, *, site_map: dict | None = None,
            client=None, models: list[str] | None = None,
            usage=None, mock: bool = False) -> dict:
    """미션 하나를 검토한다. 규칙 → 모델 순."""
    issues = rule_issues(goal)
    if issues:
        # 규칙에서 걸리면 모델을 부르지 않는다. 답이 이미 확실하다.
        return {"status": "invalid", "success_criteria": None, "check": {},
                "issues": issues, "generated_by": "rule"}

    if mock or client is None:
        return {"status": "ok",
                "success_criteria": "페르소나가 목표를 이뤘다고 판단하면 성공",
                "check": {}, "issues": [], "generated_by": "rule"}

    from .llm import chat_json_any

    lines = ["미션: %s" % goal.strip()]
    if site_map and site_map.get("pages"):
        lines.append("")
        lines.append("이 사이트의 화면들:")
        for p in site_map["pages"][:8]:
            lines.append("- %s (%s)" % (p.get("title") or p["path"], p["path"]))
    body = chat_json_any(client, models=models or config.models("goals"),
                         system=SYSTEM, user="\n".join(lines),
                         temperature=config.TEMP_GOALS, usage=usage)

    ok = bool(body.get("ok"))
    check = body.get("check") or {}
    if not isinstance(check, dict):
        check = {}
    check = {k: str(v) for k, v in check.items()
             if k in ("url_contains", "text_contains") and str(v or "").strip()}

    if ok:
        return {"status": "ok",
                "success_criteria": str(body.get("criteria") or "").strip()
                or "페르소나가 목표를 이뤘다고 판단하면 성공",
                "check": check, "issues": [], "generated_by": "gemini"}
    return {"status": "invalid", "success_criteria": None, "check": {},
            "issues": [{"kind": "judgement",
                        "message": str(body.get("reason") or "이 미션으로는 검사하기 어렵습니다."),
                        "fix": str(body.get("suggestion") or JUDGEMENT_HINT)}],
            "generated_by": "gemini"}


def as_json(result: dict) -> str:
    return json.dumps(result, ensure_ascii=False)
