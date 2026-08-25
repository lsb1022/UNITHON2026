"""미션 문장을 검사하고 성공 기준을 만들어 준다.

두 갈래가 있다.

1. **LLM (기본)** — Claude 에게 기획서 4장의 기준으로 문장을 읽히고, 성공 기준을
   한국어 한 문장으로 쓰게 한다. 규칙으로는 "결제까지 완료" 같은 정해진 꼴만 알아듣지만,
   실제 사용자는 "장바구니에 담아둔 신발 사이즈를 바꿔서 사고 싶어요"처럼 쓴다.
   그런 문장에서 도착점을 찾아내는 건 문자열 규칙으로 될 일이 아니다.
   `ANTHROPIC_API_KEY` 가 있어야 돈다.

2. **규칙 (대비책)** — 키가 없거나 호출이 실패하면 예전 규칙으로 떨어진다.
   틀린 답보다는 좁은 답이 낫고, 데모 중에 화면이 죽는 것보다는 훨씬 낫다.
   응답의 `generated_by` 로 어느 쪽이 답했는지 알 수 있다.

검사 항목은 기획서 4장의 "좋은 미션은 이렇게 써요"를 그대로 옮긴 것이다:
  - 버튼 이름을 직접 알려주기보다 사용자의 목적을 적는다
  - 한 미션에는 하나의 완료 목표만 넣는다
  - 탐색 중에는 결함 분석을 시키지 않는다
"""

from __future__ import annotations

import logging
import os
import re
from dataclasses import asdict, dataclass

log = logging.getLogger(__name__)

MIN_LENGTH = 10
MAX_LENGTH = 200

#: UI 요소를 직접 지시하는 표현. 길찾기 마찰이 통째로 사라진다.
UI_HINT = re.compile(r"(버튼|클릭|눌러|누르|탭하|링크를 눌|메뉴를 눌|상단 우측|좌측 상단)")

#: 결함을 찾으라는 지시. 기획서 4장 — 이러면 멀쩡한 화면에서도 목록을 만들어낸다.
DEFECT_HUNT = re.compile(r"(문제점|결함|버그|오류를 찾|불편한 점|개선점|이상한 점|UX 문제)")

#: 앞말이 연결어미로 끝나면 거기서 목표 구절이 시작된다 ("…골라 결제" -> "결제")
CONNECTIVE_END = ("고", "서", "라", "며", "아", "어", "야", "은", "는", "을", "를")

COMPLETION_WORDS = ("완료", "제출", "결제", "주문", "가입", "신청", "예약", "구매")

#: 그 자체로는 무엇을 끝냈는지 알 수 없는 말. 앞에서 목적어를 찾아야 한다.
GENERIC_VERBS = ("완료", "제출", "끝내")

#: 토큰 끝에 붙는 조사. 떼어내야 "회원가입을" 이 "회원가입" 이 된다.
PARTICLES = ("까지", "으로", "에서", "를", "을", "이", "가", "은", "는", "에", "의", "도", "해")


@dataclass
class Issue:
    kind: str
    message: str
    fix: str


@dataclass
class MissionAnalysis:
    #: ok = 그대로 써도 됨 / warning = 고치면 더 좋음 / invalid = 이대로는 못 돌림
    status: str
    success_criteria: str | None
    issues: list[dict]
    generated_by: str


# --------------------------------------------------------------------------- #
# LLM
# --------------------------------------------------------------------------- #

MODEL = os.environ.get("UXLAB_MISSION_MODEL", "claude-opus-5")

SYSTEM = """당신은 AI 페르소나 UX 테스트 도구의 미션 검토자입니다.

사용자가 쓴 "미션"은 가상의 사용자(페르소나)가 웹사이트에서 수행할 목표입니다.
페르소나는 이 문장만 읽고 사이트를 처음 방문해 스스로 길을 찾습니다.

당신의 일은 두 가지입니다.

## 1. 성공 기준 만들기
미션이 어디에 도착하면 끝나는지를 찾아, 채점에 쓸 한국어 한 문장으로 적습니다.
- 형식: "<도착 지점> 화면에 도착하면 성공으로 볼게요."
- 도착 지점은 화면 이름처럼 짧은 명사구로 적습니다 (예: "주문 완료", "예약 확정", "견적 요청 완료").
- 미션에 없는 단계를 지어내지 않습니다. 사용자가 쓴 목표 그대로를 도착 지점으로 삼습니다.
- 끝나는 지점을 정말 못 찾겠으면 success_criteria 를 null 로 두고 no_goal 이슈를 냅니다.

## 2. 문제 찾기
아래 항목만 봅니다. 해당 없으면 이슈를 만들지 마세요 — 억지로 채우면 사용자가 멀쩡한 미션을 고칩니다.

- `ui_hint`: 버튼 이름·클릭 위치 등 조작 방법을 알려줌.
  길을 알려주면 헤매지 않으므로 길찾기 마찰이 측정되지 않습니다.
  ※ "장바구니", "마이페이지"처럼 사이트의 기능·영역을 목적으로 언급하는 것은 문제가 아닙니다.
     "우측 상단 장바구니 버튼을 누르세요"처럼 조작을 지시할 때만 잡으세요.
- `defect_hunt`: 문제점·버그·개선점을 찾아 달라고 지시함.
  탐색 중 결함을 물으면 멀쩡한 화면에서도 목록을 만들어내 오탐률이 무너집니다.
- `multiple_goals`: 서로 독립적인 완료 목표가 둘 이상.
  ※ "로그인해서 결제까지"처럼 앞 단계가 뒤 단계의 전제인 것은 목표 하나입니다. 잡지 마세요.
- `no_goal`: 끝나는 지점이 없음 (둘러보기·구경 등).
- `too_short`: 무엇을 해야 하는지 알 수 없을 만큼 짧음.
- `too_long`: 200자를 넘겨 목표가 흐려짐.

## status
- `invalid`: defect_hunt / no_goal / too_short / too_long 중 하나라도 있으면. 이대로 돌리면 결과를 못 씁니다.
- `warning`: ui_hint / multiple_goals 만 있으면. 돌아가긴 하지만 측정이 흐려집니다.
- `ok`: 이슈 없음.

message 는 무엇이 문제인지, fix 는 어떻게 고치면 되는지를 각각 한 문장으로,
사용자에게 말하듯 존댓말로 적습니다. 사용자를 탓하지 않습니다."""

SCHEMA = {
    "type": "object",
    "properties": {
        "status": {"type": "string", "enum": ["ok", "warning", "invalid"]},
        "success_criteria": {
            "type": ["string", "null"],
            "description": "채점에 쓸 성공 기준 한 문장. 도착점을 못 찾으면 null.",
        },
        "issues": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "kind": {
                        "type": "string",
                        "enum": [
                            "ui_hint",
                            "defect_hunt",
                            "multiple_goals",
                            "no_goal",
                            "too_short",
                            "too_long",
                        ],
                    },
                    "message": {"type": "string"},
                    "fix": {"type": "string"},
                },
                "required": ["kind", "message", "fix"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["status", "success_criteria", "issues"],
    "additionalProperties": False,
}

BLOCKING = {"defect_hunt", "no_goal", "too_short", "too_long"}

_client = None


def _get_client():
    """API 키가 있을 때만 클라이언트를 만든다. 없으면 None."""
    global _client
    if _client is not None:
        return _client
    if not os.environ.get("ANTHROPIC_API_KEY"):
        return None
    try:
        import anthropic
    except ImportError:
        return None
    try:
        _client = anthropic.Anthropic()
    except Exception as error:
        log.warning("Anthropic 클라이언트를 만들지 못했습니다: %s", error)
        return None
    return _client


def _analyze_with_llm(text: str) -> MissionAnalysis | None:
    client = _get_client()
    if client is None:
        return None

    try:
        import json

        response = client.messages.create(
            model=MODEL,
            max_tokens=2000,
            system=SYSTEM,
            # 문장 하나를 읽는 일이다. 깊게 생각할수록 이슈를 억지로 만들어낸다.
            output_config={"format": {"type": "json_schema", "schema": SCHEMA}, "effort": "low"},
            messages=[{"role": "user", "content": f"미션:\n{text}"}],
        )
        if response.stop_reason == "refusal":
            return None
        payload = next(b.text for b in response.content if b.type == "text")
        data = json.loads(payload)
    except Exception as error:
        # 크레딧 소진(429), 네트워크 단절, 스키마 위반 — 어느 쪽이든 규칙으로 떨어진다.
        log.info("미션 분석 LLM 호출 실패, 규칙으로 대체합니다: %s", error)
        return None

    issues = [
        {"kind": i["kind"], "message": i["message"], "fix": i["fix"]}
        for i in data.get("issues", [])
    ]
    criteria = data.get("success_criteria") or None

    # status 는 모델이 고르지만, 규칙과 어긋나면 규칙을 따른다. 화면의 색(빨강/초록)이
    # 이슈 목록과 따로 놀면 사용자는 무엇을 믿어야 할지 알 수 없다.
    kinds = {i["kind"] for i in issues}
    if kinds & BLOCKING or criteria is None:
        status = "invalid"
    elif kinds:
        status = "warning"
    else:
        status = "ok"

    return MissionAnalysis(status, criteria, issues, "llm")


# --------------------------------------------------------------------------- #
# 규칙 (대비책)
# --------------------------------------------------------------------------- #


def _completion_spans(text: str) -> list[tuple[int, str]]:
    """완료를 뜻하는 단어의 위치. '결제까지 완료'처럼 붙어 있는 것은 하나로 본다."""
    hits = sorted(
        (m.start(), m.group())
        for word in COMPLETION_WORDS
        for m in re.finditer(word, text)
    )

    merged: list[tuple[int, str]] = []
    for start, word in hits:
        # 앞 것과 8자 이내로 붙어 있으면 같은 목표를 두 단어로 쓴 것이다.
        if merged and start - merged[-1][0] <= 8:
            continue
        merged.append((start, word))
    return merged


def _strip_particles(token: str) -> str:
    text = token.strip(" ,.")
    for particle in PARTICLES:
        if len(text) > len(particle) and text.endswith(particle):
            return text[: -len(particle)]
    return text


def _token_at(text: str, index: int) -> str:
    """index 위치를 포함하는 공백 구분 토큰을 조사 없이 돌려준다."""
    left = text.rfind(" ", 0, index) + 1
    right = text.find(" ", index)
    return _strip_particles(text[left : right if right != -1 else len(text)])


def generate_success_criteria(prompt: str) -> str | None:
    """미션의 마지막 목표 구절에서 성공 기준 문장을 만든다.

    "…견적 요청까지 완료해 주세요" -> "견적 요청 완료 화면에 도착하면 성공으로 볼게요."
    "…결제까지 완료해 주세요"      -> "결제 완료 화면에 도착하면 성공으로 볼게요."
    """
    spans = _completion_spans(prompt)
    if not spans:
        return None

    # 마지막 목표 무리에 속한 단어들을 모은다 ("결제" + "완료").
    start = spans[-1][0]
    group = [_token_at(prompt, pos) for pos, _ in _all_spans_from(prompt, start)]
    group = [word for i, word in enumerate(group) if word and word not in group[:i]]

    if len(group) >= 2:
        phrase = f"{group[0]} {group[-1]}"
    else:
        verb = group[0] if group else spans[-1][1]
        phrase = verb
        if any(verb.startswith(g) for g in GENERIC_VERBS):
            # "완료" 만으로는 무엇을 끝냈는지 알 수 없다. 앞의 명사구를 붙인다.
            head = prompt[:start].rstrip().removesuffix("까지").rstrip()
            tokens: list[str] = []
            for token in reversed(head.split()):
                if tokens and token.endswith(CONNECTIVE_END):
                    break
                tokens.insert(0, _strip_particles(token))
                if len(tokens) >= 2:
                    break
            target = " ".join(t for t in tokens if t)
            if target:
                phrase = f"{target} {verb}"

    return f"{phrase} 화면에 도착하면 성공으로 볼게요."


def _all_spans_from(text: str, start: int) -> list[tuple[int, str]]:
    """start 이후에 붙어 있는 완료 단어들 (병합된 무리 전체)."""
    hits = sorted(
        (m.start(), m.group())
        for word in COMPLETION_WORDS
        for m in re.finditer(word, text)
        if m.start() >= start
    )
    group: list[tuple[int, str]] = []
    for pos, word in hits:
        if group and pos - group[-1][0] > 8:
            break
        group.append((pos, word))
    return group


def _analyze_with_rules(text: str) -> MissionAnalysis:
    issues: list[Issue] = []

    if len(text) < MIN_LENGTH:
        issues.append(
            Issue(
                "too_short",
                "무엇을 끝내야 하는지 알 수 없어요.",
                "페르소나가 '무엇을 해서 어디까지 가면 되는지'를 한 문장으로 적어 주세요.",
            )
        )
        return MissionAnalysis("invalid", None, [asdict(i) for i in issues], "rules")

    if len(text) > MAX_LENGTH:
        issues.append(
            Issue("too_long", f"{MAX_LENGTH}자를 넘었어요.", "핵심 목표 한 가지만 남겨 주세요.")
        )

    if DEFECT_HUNT.search(text):
        issues.append(
            Issue(
                "defect_hunt",
                "결함을 찾으라고 지시하고 있어요.",
                "탐색 중에 문제점을 물으면 멀쩡한 화면에서도 목록을 만들어내 오탐률이 무너져요. "
                "결함 판정은 실행이 끝난 뒤 채점 단계에서 따로 해요.",
            )
        )

    if UI_HINT.search(text):
        issues.append(
            Issue(
                "ui_hint",
                "버튼·클릭처럼 조작 방법을 직접 알려주고 있어요.",
                "길을 알려주면 헤매지 않아서 마찰이 측정되지 않아요. 목적만 적어 주세요.",
            )
        )

    if len(_completion_spans(text)) >= 2:
        issues.append(
            Issue(
                "multiple_goals",
                "완료 목표가 둘 이상으로 보여요.",
                "한 미션에는 완료 목표를 하나만 넣어야 어디서 막혔는지 가려낼 수 있어요.",
            )
        )

    criteria = generate_success_criteria(text)
    if criteria is None:
        issues.append(
            Issue(
                "no_goal",
                "끝나는 지점을 찾지 못했어요.",
                "'…까지 완료해 주세요'처럼 도착점을 넣으면 성공 기준을 자동으로 만들어요.",
            )
        )

    status = (
        "invalid"
        if any(i.kind in BLOCKING for i in issues)
        else ("warning" if issues else "ok")
    )

    return MissionAnalysis(status, criteria, [asdict(i) for i in issues], "rules")


# --------------------------------------------------------------------------- #


def analyze(prompt: str) -> MissionAnalysis:
    text = prompt.strip()

    # 한두 글자짜리는 LLM 에 보낼 것도 없다. 타이핑 중에도 불리는 엔드포인트라
    # 첫 글자마다 호출하면 돈과 시간이 샌다.
    if len(text) < MIN_LENGTH:
        return _analyze_with_rules(text)

    return _analyze_with_llm(text) or _analyze_with_rules(text)


def analyze_as_dict(prompt: str) -> dict:
    return asdict(analyze(prompt))
