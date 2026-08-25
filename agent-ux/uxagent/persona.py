"""페르소나 조립 — 특성 4축 x 1~5단계로 100명.

설계 지시(2026-08-25)에 따라 축을 다시 잡았다.

  숙련도    1 사이트가 낯섦      … 5 온라인 쇼핑에 능숙
  주의 지속  1 거의 안 읽음       … 5 끝까지 읽음
  인내심    1 바로 포기          … 5 될 때까지 시도
  탐색 범위  1 한 화면만          … 5 곳곳을 둘러봄

5^4 = 625조합이라 100명 전원이 서로 다른 조합을 받는다. 각 축의 값은
**정확히 20명씩** 배분한다 — 균등하지 않으면 "숙련도가 낮으면 어떤가"를
비교할 때 표본 크기가 달라 결론이 흔들린다.

## 목표는 한 번만 저장한다

목표 문자열과 시작 지점은 전원 동일하므로 파일 상단에 한 번만 둔다.
100명에게 복사하면 파일이 커지고, 나중에 목표를 고칠 때 100군데를 고쳐야 한다.

## 문장은 딕셔너리로 조립한다

LLM에게 페르소나 문장을 쓰게 하지 않는다. 같은 값이 항상 같은 문장이어야
"숙련도 2인 사람들"을 묶어 비교할 수 있다. 배경 서사도 넣지 않는다 —
길수록 모델이 서사에 맞춰 행동해 페르소나끼리 오히려 닮아진다.

## 강제할 수 있는 것은 코드가 강제한다

문장만 주면 모델이 무시한다. 숫자로 자연스럽게 옮겨지는 축(주의·인내)은
전 단계를 강제하고, 중간값 정의가 애매한 축(숙련도·탐색)은 **극단만** 강제한다.
강제 구간(1-2 / 4-5)이 분석 구간과 일치하는 것은 의도적이다.
"""
from __future__ import annotations

import random

from . import config

AXES = ("literacy", "attention", "patience", "breadth")

AXIS_LABEL = {
    "literacy": "숙련도",
    "attention": "주의 지속",
    "patience": "인내심",
    "breadth": "탐색 범위",
}

# 값 -> 문장. 이 딕셔너리가 프롬프트의 유일한 출처다.
SENTENCES = {
    "literacy": {
        1: "이런 사이트를 써본 적이 거의 없습니다.",
        2: "온라인 쇼핑이 아직 익숙하지 않습니다.",
        3: "가끔 온라인 쇼핑을 합니다.",
        4: "온라인 쇼핑을 자주 합니다.",
        5: "온라인 쇼핑에 매우 익숙합니다.",
    },
    "attention": {
        1: "화면을 거의 읽지 않고 눈에 띄는 것만 누릅니다.",
        2: "필요한 부분만 훑어봅니다.",
        3: "중요해 보이는 내용은 읽습니다.",
        4: "대부분의 안내 문구를 읽습니다.",
        5: "화면의 글을 처음부터 끝까지 읽습니다.",
    },
    "patience": {
        1: "조금만 막혀도 바로 그만둡니다.",
        2: "몇 번 시도해보고 안 되면 나갑니다.",
        3: "어느 정도는 다시 시도해봅니다.",
        4: "잘 안 돼도 방법을 찾아봅니다.",
        5: "될 때까지 여러 방법을 시도합니다.",
    },
    "breadth": {
        1: "한 화면만 보고 결정합니다.",
        2: "필요한 페이지만 최소한으로 이동합니다.",
        3: "몇 군데는 둘러봅니다.",
        4: "여러 페이지를 오가며 비교합니다.",
        5: "사이트 곳곳을 폭넓게 둘러봅니다.",
    },
}

# ── 코드 강제 ─────────────────────────────────────────────────────

# 주의 지속 -> 한 화면에 머무는 시간(ms). 자동 팝업이 10초 후에 뜨므로
# 4~5단계만 그 결함을 만난다. 이 표가 곧 '누가 무엇을 마주치는가'를 정한다.
DWELL_MS = {1: (800, 1500), 2: (1500, 3000), 3: (3000, 6000),
            4: (6000, 10000), 5: (10000, 15000)}

# 인내심 -> (허용 시도 횟수, 최대 스텝).
# '시도 횟수'는 아무 변화도 못 만든 행동의 허용치다. 넘으면 그만둔다.
PATIENCE = {1: ((4, 7), 15), 2: ((8, 12), 20), 3: ((13, 18), 25),
            4: ((19, 24), 30), 5: ((25, 30), 35)}

BASE_ACTIONS = ["click", "type", "select", "scroll", "back", "wait"]
# 주소창 입력. 서툰 사람에게 허용하면 결제 페이지로 순간이동해
# 길찾기 마찰이 통째로 측정에서 사라진다.
URL_ACTION = "goto"

# 탐색 범위 = 결정하기 전에 **대안을 몇 개나 보는가**.
# 목표로 가는 길(장바구니 -> 결제 -> 완료)은 둘러보는 것이 아니라 거쳐가는 곳이므로
# 세지 않는다. 같은 종류 화면(상품 상세, 목록)을 몇 개까지 열어보는지만 센다.
#   1 한 화면만 보고 결정  -> 상품 1개만 보고 정한다
#   2 필요한 최소한        -> 2개까지 비교
#   3 이상                 -> 제한 없음 (극단만 강제한다는 원칙)
# 이렇게 세면 상품 하나만 보고 바로 사는 사람도 결제를 끝까지 마칠 수 있다.
COMPARE_CAP = {1: 1, 2: 2, 3: 0, 4: 0, 5: 0}


def _balanced(n: int, rng: random.Random) -> list[int]:
    """1~5 를 정확히 n/5 명씩. 남는 인원은 앞 값부터 하나씩."""
    per, rest = divmod(n, 5)
    vals = [v for v in range(1, 6) for _ in range(per)] + list(range(1, 1 + rest))
    rng.shuffle(vals)
    return vals


def combos(n: int = config.N_PERSONAS, seed: int = config.PERSONA_SEED) -> list[dict]:
    """축마다 균등 분포를 만들고, 조합이 겹치지 않게 다듬는다.

    균등 분포와 조합 유일성을 동시에 만족시켜야 한다. 축을 따로 섞으면
    드물게 같은 조합이 나오므로, 겹칠 때만 한 축의 값을 다른 사람과 맞바꾼다
    (맞바꾸므로 분포는 그대로다).
    """
    rng = random.Random(seed)
    cols = {a: _balanced(n, rng) for a in AXES}
    rows = [{a: cols[a][i] for a in AXES} for i in range(n)]

    seen: dict[tuple, int] = {}
    for i, row in enumerate(rows):
        key = tuple(row[a] for a in AXES)
        for _ in range(200):
            if key not in seen:
                break
            # 겹쳤다. 한 축을 골라 다른 사람과 값을 맞바꾼다.
            a = rng.choice(AXES)
            j = rng.randrange(n)
            if j == i:
                continue
            rows[i][a], rows[j][a] = rows[j][a], rows[i][a]
            key = tuple(rows[i][a2] for a2 in AXES)
        seen[key] = i
    return rows


def label(traits: dict) -> str:
    return "숙련%d·주의%d·인내%d·탐색%d" % tuple(traits[a] for a in AXES)


def build_prompt(traits: dict, goal: str) -> str:
    """특성 문장 4줄 + 목표 1줄. 서사는 넣지 않는다."""
    lines = [SENTENCES[a][traits[a]] for a in AXES]
    return "\n".join(lines) + "\n목표: %s" % goal


def build(goal: str, start_path: str, n: int = config.N_PERSONAS,
          seed: int = config.PERSONA_SEED) -> list[dict]:
    """목표는 전원 동일. 사람마다 다른 것은 특성과 거기서 파생된 제약뿐이다."""
    rng = random.Random(seed + 1)
    people = []
    for i, traits in enumerate(combos(n, seed)):
        prompt = build_prompt(traits, goal)
        if len(prompt) > config.PROMPT_MAX_CHARS:
            raise ValueError("프롬프트 %d자 > 상한 %d자: %s"
                             % (len(prompt), config.PROMPT_MAX_CHARS, prompt))

        lo, hi = DWELL_MS[traits["attention"]]
        (amin, amax), max_steps = PATIENCE[traits["patience"]]

        actions = list(BASE_ACTIONS)
        # 숙련도 1-2 는 주소창·검색을 쓰지 않는다. 3 이상은 제약 없음.
        url_ok = traits["literacy"] >= 3
        if url_ok:
            actions.append(URL_ACTION)

        people.append({
            "id": "P%03d" % (i + 1),
            "label": label(traits),
            "traits": traits,
            # 분석용 묶음. 원본 값은 traits 에 그대로 남는다.
            "bands": {a: ("low" if traits[a] <= 2 else
                          "high" if traits[a] >= 4 else "mid") for a in AXES},
            "prompt": prompt,
            "start_path": start_path,
            "allowed_actions": actions,
            "search_allowed": url_ok,
            "max_steps": max_steps,
            "max_idle_attempts": rng.randint(amin, amax),
            "dwell_ms": rng.randint(lo, hi),
            # 같은 종류 화면을 몇 개까지 비교하는가. 0 이면 제한 없음.
            "compare_cap": COMPARE_CAP[traits["breadth"]],
            "user_type": "new",
            "seed_state": None,
        })
    return people


# ── 시딩 (목표가 요구할 때만 쓰인다) ────────────────────────────────
# 지금 설계에서는 목표가 하나뿐이라 기본적으로 쓰지 않는다. 장바구니가 찬
# 상태에서 시작해야 하는 목표가 다시 생기면 여기를 다시 연결한다.
DEFAULT_SEED = {"cart": [{"id": 1, "color": "아이보리", "size": "M", "qty": 1}]}
TWO_ITEM_SEED = {"cart": [
    {"id": 3, "color": "화이트", "size": "250", "qty": 1},
    {"id": 10, "color": "블랙", "size": "FREE", "qty": 2},
]}


def seed_script(seed_state: dict, storage_key: str) -> str:
    """localStorage 를 직접 쓰는 JS. 러너가 첫 goto 직후 실행한다.

    사이트의 addToCart() 를 부르지 않는 이유: flawed 쪽 addToCart 자체가
    결함일 수 있다. 준비 단계가 검사 대상 코드에 의존하면 '재방문자'가
    한쪽에서만 빈 장바구니로 시작하고, 그 차이가 결함 탐지 결과로 둔갑한다.
    """
    import json as _json
    items = _json.dumps(seed_state["cart"], ensure_ascii=False)
    return """(() => {
  const want = %s;
  const P = window.PRODUCTS || [];
  const lines = want.map(w => {
    const p = P.find(x => x.id === w.id);
    if (!p) return null;
    return {key: `${w.id}|${w.color}|${w.size}`, id: w.id, name: p.name,
            price: p.price, color: w.color, size: w.size, qty: w.qty};
  }).filter(Boolean);
  localStorage.setItem(%s, JSON.stringify(lines));
  return lines.length;
})()""" % (items, _json.dumps(storage_key))
