"""페르소나 조립 — 목표 11개 x 특성 조합 16개 -> 100명.

세 가지가 여기서 정해진다.

1. **왜 11개인가.** 특성 조합이 16개다. 목표가 10개면 LCM이 80이라
   81번째부터는 앞 20명과 (조합, 목표) 쌍이 그대로 겹친다. 같은 조건을
   두 번 돌리고 표본 100이라 부르는 셈이다. 11은 16과 서로소라
   100명 전원이 서로 다른 쌍을 받는다.

2. **프롬프트는 200자 이내, 배경 서사 금지.** "35세 직장인 김민수는
   퇴근 후..." 를 넣으면 모델이 그 서사에 맞는 행동을 지어내고, 그 문장은
   스텝마다 30번 다시 전송된다. 특성 -> 문장 매핑 딕셔너리로 조립하면
   같은 특성이 항상 같은 문장이 되어 조합 간 비교가 성립한다.

3. **상태는 코드가 만든다.** 답사에서 정한 것과 같은 원칙이다.
   지도 = 상태와 무관한 서술(LLM) / 스냅샷 = 상태에 의존하는 수치(코드).
   여기서도 목표 문장은 LLM이 쓰지만 `seed_state`(장바구니에 뭐가 담겨
   있는가)는 코드가 만든다. LLM이 만든 장바구니 JSON은 상품 id·가격이
   틀려도 아무도 못 잡는다.

⚠ `seed_state` 에 localStorage 키를 넣지 않는다. 키가 변형마다 다른데
   (`moji_cart_clean` / `moji_cart_flawed`) 페르소나 파일은 양쪽에 동일하게
   투입되므로(결정 6), 키를 박으면 한쪽이 조용히 빈 장바구니가 되고
   유형 C 목표 전부가 무력화된다. 키는 러너가 `config.cart_key(variant)`
   에서 읽어 `seed_script()` 에 넘긴다.
"""
from __future__ import annotations

import json

from . import config

# ── 특성 축 4개 x 2 = 16조합 ───────────────────────────────────────
# 축을 늘리면 조합이 32가 되어 목표 11개와 다시 서로소가 아니게 되는지
# 확인해야 한다 (gcd(11,32)=1 이라 32도 안전하지만, 100명으로는 조합당
# 3명뿐이라 조합별 비교의 표본이 무너진다).
AXES = {
    "literacy": ("savvy", "novice"),    # 온라인 쇼핑 숙련도
    "patience": ("patient", "hasty"),   # 기다림
    "reading":  ("reader", "scanner"),  # 화면을 읽는가 훑는가
    "visit":    ("new", "returning"),   # 첫 방문인가
}

# 특성 -> 문장. 이 딕셔너리가 프롬프트의 유일한 출처다.
SENTENCES = {
    "literacy": {
        "savvy":  "온라인 쇼핑에 익숙하다.",
        "novice": "온라인 쇼핑이 서툴다.",
    },
    "patience": {
        "patient": "화면이 바뀌지 않아도 잠시 기다린다.",
        "hasty":   "오래 걸리면 바로 그만둔다.",
    },
    "reading": {
        "reader":  "화면의 글을 처음부터 읽는다.",
        "scanner": "글은 훑고 눈에 띄는 것부터 누른다.",
    },
    "visit": {
        "new":       "이 사이트는 처음이다.",
        "returning": "전에 와서 장바구니에 담아둔 적이 있다.",
    },
}

LABELS = {
    "savvy": "익숙", "novice": "서툼",
    "patient": "여유", "hasty": "조급",
    "reader": "정독", "scanner": "훑기",
    "new": "신규", "returning": "재방문",
}

# 러너가 실제로 강제하는 목록. 목록 밖 행동은 blocked_action 으로 기록된다.
BASE_ACTIONS = ["click", "type", "select", "scroll", "back", "wait"]
# URL을 직접 치는 것은 숙련자만 한다. 서툰 사람이 주소창으로 결제 페이지에
# 바로 가버리면 '길찾기 마찰'이 통째로 측정에서 사라진다.
SAVVY_ONLY = ["goto"]

# 한 페이지에 머무는 시간. D-26(자동 팝업)은 로드 10초 후에 뜬다.
# 전원이 5초 만에 떠나면 Critical 결함 하나를 아무도 만나지 못한다.
# 정독 x 여유 조합(16 중 4개 = 100명 중 25명)이 10초 문턱을 넘도록 잡았다.
DWELL_MS = {
    ("reader", "patient"):  12000,
    ("reader", "hasty"):     6000,
    ("scanner", "patient"):  4000,
    ("scanner", "hasty"):    1500,
}


def combos() -> list[dict]:
    """16조합을 항상 같은 순서로 만든다. 순서가 흔들리면 실행 간 비교가 깨진다."""
    out = []
    for i in range(16):
        out.append({
            "literacy": AXES["literacy"][(i >> 0) & 1],
            "patience": AXES["patience"][(i >> 1) & 1],
            "reading":  AXES["reading"][(i >> 2) & 1],
            "visit":    AXES["visit"][(i >> 3) & 1],
        })
    return out


def combo_label(t: dict) -> str:
    return "·".join(LABELS[t[a]] for a in AXES)


def build_prompt(traits: dict, goal: dict, seeded: bool) -> str:
    """특성 문장 4개 + 목표 1줄. 서사는 넣지 않는다.

    seeded=True 면 visit 축이 무엇이든 '담아둔 적 있다' 쪽 문장을 쓴다.
    장바구니에 물건이 들어있는데 "이 사이트는 처음이다"라고 말하면
    모델이 그 모순을 스스로 메우려 엉뚱한 행동을 한다.
    """
    visit = "returning" if seeded else traits["visit"]
    lines = [
        SENTENCES["literacy"][traits["literacy"]],
        SENTENCES["patience"][traits["patience"]],
        SENTENCES["reading"][traits["reading"]],
        SENTENCES["visit"][visit],
        "목표: %s" % goal["text"],
    ]
    return " ".join(lines[:4]) + "\n" + lines[4]


def build(goals: list[dict], n: int = config.N_PERSONAS) -> list[dict]:
    """(조합 i%16, 목표 i%11) 로 n명. n<=176 이면 쌍이 겹치지 않는다."""
    if len(goals) != config.N_GOALS:
        raise ValueError("목표는 %d개여야 합니다 (받은 값 %d개). "
                         "16조합과 서로소가 아니면 뒤쪽 페르소나가 앞을 반복합니다."
                         % (config.N_GOALS, len(goals)))
    cs = combos()
    people = []
    for i in range(n):
        traits = cs[i % len(cs)]
        goal = goals[i % len(goals)]

        # 시딩 규칙: 목표가 요구하면 목표의 것을, 아니면 재방문자에게 기본 1건.
        # 재방문자를 빈 장바구니로 두면 '재방문'이 이름뿐인 특성이 된다.
        seed = goal.get("seed_state") or (
            DEFAULT_SEED if traits["visit"] == "returning" else None)

        prompt = build_prompt(traits, goal, seed is not None)
        if len(prompt) > config.PROMPT_MAX_CHARS:
            raise ValueError("프롬프트 %d자 > 상한 %d자: %s"
                             % (len(prompt), config.PROMPT_MAX_CHARS, prompt))

        actions = list(BASE_ACTIONS)
        if traits["literacy"] == "savvy":
            actions += SAVVY_ONLY

        people.append({
            "id": "P%03d" % (i + 1),
            "label": "%s / %s" % (combo_label(traits), goal["id"]),
            "traits": traits,
            "combo_index": i % len(cs),
            "goal_id": goal["id"],
            "goal_type": goal["type"],
            "goal": goal["text"],
            "success": goal.get("success"),
            "start_path": goal["start_path"],
            "prompt": prompt,
            "allowed_actions": actions,
            "max_steps": 20 if traits["patience"] == "hasty" else config.MAX_STEPS,
            "dwell_ms": DWELL_MS[(traits["reading"], traits["patience"])],
            "user_type": "returning" if seed else "new",
            "seed_state": seed,
        })
    return people


# ── 시딩 ──────────────────────────────────────────────────────────
# 담아둔 상품은 코드가 고른다. 값이 두 군데 있으면 어긋나므로 여기가 유일한 출처.
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

    가격·이름은 window.PRODUCTS(두 변형이 공유하는 파일)에서 읽는다.
    파이썬에 가격표를 복사해두면 픽스처를 고칠 때 반드시 어긋난다.
    """
    items = json.dumps(seed_state["cart"], ensure_ascii=False)
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
})()""" % (items, json.dumps(storage_key))
