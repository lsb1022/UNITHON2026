"""탐색 기록(trace) 스키마와 기록기.

run.py 가 쓸 형식을 여기서 못박는다. 뷰어가 읽는 것도 이 형식 하나뿐이다.

설계 원칙 셋:

1. **생각을 남긴다.** 행동만 남기면 "뭘 했나"만 보이고, 생각을 남겨야
   "왜 그랬나"가 보인다. 차별점 ③(투명한 사고 기록)의 실체가 이 필드다.

2. **에이전트는 좌표로 누르지 않는다.** 이름(data-agent-id)으로 지목한다.
   `resolved` 좌표는 '그 순간 그 요소가 화면 어디에 있었나'를 되짚기 위한
   기록이지, 좌표로 조작했다는 뜻이 아니다. 발표에서 헷갈리면 안 된다.

3. **스텝마다 스냅샷을 통째로 남긴다.** 나중에 다시 계산할 수 없기 때문이다.
   장바구니에 3개가 담긴 상태의 접힘선은 그 순간에만 존재한다.
   페르소나당 30스텝 x 40요소 ≈ 100KB 라 100명이어도 10MB 안쪽이다.
"""
from __future__ import annotations

import json
import os
from datetime import datetime

SCHEMA_VERSION = 1

# 종료 사유. '포기'와 '스텝 소진'은 다른 신호다.
# 포기가 몰리는 지점이 진짜 마찰 지점이다.
# budget_stop 은 우리가 예산 상한에서 끊은 것이지 사람이 포기한 게 아니다.
# 이걸 gave_up 으로 적으면 마찰 지점 통계가 오염된다.
END_REASONS = ("goal_reached", "gave_up", "max_steps", "loop_detected",
               "budget_stop", "error")

# 와이어프레임을 그리는 데 필요한 요소 필드만 남긴다.
# 전체 스냅샷을 그대로 저장하면 로그가 4배로 불어난다.
_KEEP = ("id", "tag", "text", "page_x", "page_y", "w", "h",
         "below_fold", "occluded", "contrast", "font_size",
         "disabled_look", "disabled_attr", "keyboard_reachable",
         "input_type", "value", "checked")


def counts_of(els: list[dict]) -> dict:
    """화면 전체의 집계. **요소를 추려내기 전에** 뽑아 둔다.

    추린 목록으로 세면 "화면에 저대비가 3개뿐"처럼 줄어든 숫자가 나온다.
    보고서와 일기가 쓰는 것은 화면 전체의 값이므로 여기서 못박는다.
    """
    return {
        "total": len(els),
        "below_fold": sum(1 for e in els if e.get("below_fold")),
        "occluded": sum(1 for e in els if e.get("occluded")),
        "low_contrast": sum(1 for e in els
                            if (e.get("contrast") or 99) < 3.0
                            and not e.get("disabled_attr")),
        "keyboard_unreachable": sum(1 for e in els
                                    if not e.get("keyboard_reachable")),
    }


def slim(snap: dict, shown_ids: set | None = None) -> dict:
    """스냅샷에서 리플레이에 필요한 것만 추린다.

    `shown_ids` 를 주면 **그 사람이 실제로 본 요소만** 남긴다.

    예전에는 화면의 모든 요소를 스텝마다 통째로 저장했다. 우리 테스트베드는
    한 화면에 20~40개라 티가 안 났는데, 위키백과에서 한 스텝에 950개가 잡히며
    기록 하나가 3.5MB 가 됐다. 프롬프트에 25개만 들어가므로 나머지 925개는
    그 사람이 본 적도 없는 것들이다.

    지운 것의 집계는 `counts` 로 남겨 보고서 숫자가 줄어들지 않게 한다.
    """
    els = snap["elements"]
    kept = ([e for e in els if e["id"] in shown_ids]
            if shown_ids is not None else els)
    return {
        "url": snap["url"],
        "title": snap["title"],
        "scroll_y": snap["scroll_y"],
        "fold_y": snap["fold_y"],
        "page_height": snap["page_height"],
        "viewport": snap["viewport"],
        "horizontal_scroll": snap["horizontal_scroll"],
        "body_contrast": snap["body_contrast"],
        "body_font_size": snap["body_font_size"],
        "visible_text": snap["visible_text"][:300],
        # 화면 전체의 집계. elements 를 추려도 이 숫자는 안 줄어든다.
        "counts": counts_of(els),
        "elements": [{k: e.get(k) for k in _KEEP} for e in kept],
    }


def step(n: int, *, thought: str, action: dict, snapshot: dict,
         resolved: dict | None = None, outcome: dict | None = None,
         map_slice_used: bool = False, map_miss: bool = False,
         blocked_action: dict | None = None, elapsed_ms: int = 0) -> dict:
    """스텝 하나.

    action  : {"type": "click"|"type"|"scroll"|"back"|"goto"|"wait", "target": "link_3", ...}
    resolved: 그 순간 target 요소의 문서 기준 위치. 못 찾았으면 None
    outcome : {"url_after": ..., "changed": bool, "note": ...}
    """
    return {
        "step": n,
        "thought": thought,
        "action": action,
        "resolved": resolved,
        "outcome": outcome or {},
        "map_slice_used": map_slice_used,
        "map_miss": map_miss,
        "blocked_action": blocked_action,
        "elapsed_ms": elapsed_ms,
        "snapshot": snapshot,
    }


def resolve(snapshot: dict, agent_id: str | None) -> dict | None:
    """지목된 이름을 그 순간의 문서 좌표로 되짚는다."""
    if not agent_id:
        return None
    for e in snapshot["elements"]:
        if e["id"] == agent_id:
            return {"x": e["page_x"], "y": e["page_y"], "w": e["w"], "h": e["h"],
                    "text": e["text"]}
    return None


class Trace:
    """페르소나 한 명의 기록. 한 명 끝날 때마다 즉시 저장한다.
    87번째에서 죽어도 앞의 86명이 남아야 한다."""

    def __init__(self, run_id: str, persona: dict, variant: str,
                 log_root: str = "logs"):
        self.run_id = run_id
        self.persona = persona
        self.variant = variant
        self.dir = os.path.join(log_root, run_id)
        self.steps: list[dict] = []
        self.started = datetime.now().isoformat(timespec="seconds")
        self.end_reason: str | None = None
        # 준비 단계에서 일어난 일 (시딩 줄 수 등). 기록에 없으면 나중에
        # '재방문자인데 장바구니가 비어 있었다'를 구분할 수 없다.
        self.extra: dict = {}

    def add(self, s: dict) -> None:
        self.steps.append(s)

    def finish(self, end_reason: str, note: str = "") -> str:
        if end_reason not in END_REASONS:
            raise ValueError("알 수 없는 종료 사유: %s" % end_reason)
        self.end_reason = end_reason
        os.makedirs(self.dir, exist_ok=True)
        path = os.path.join(self.dir, "%s.json" % self.persona["id"])
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.as_dict(note), f, ensure_ascii=False, indent=1)
        return path

    def as_dict(self, note: str = "") -> dict:
        return {
            **self.extra,
            "schema": SCHEMA_VERSION,
            "run_id": self.run_id,
            "variant": self.variant,
            "persona": self.persona,
            "started_at": self.started,
            "ended_at": datetime.now().isoformat(timespec="seconds"),
            "end_reason": self.end_reason,
            "note": note,
            "steps": self.steps,
        }


def write_index(run_id: str, variant: str, traces: list[dict],
                log_root: str = "logs", extra: dict | None = None) -> str:
    """뷰어가 처음 읽는 목록 파일. 페르소나 본문은 각자 파일에 있다."""
    d = os.path.join(log_root, run_id)
    os.makedirs(d, exist_ok=True)
    path = os.path.join(d, "index.json")
    payload = {
        "schema": SCHEMA_VERSION,
        "run_id": run_id,
        "variant": variant,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "personas": [
            {
                "id": t["persona"]["id"],
                "label": t["persona"].get("label", t["persona"]["id"]),
                "goal": t["persona"].get("goal"),
                "traits": t["persona"].get("traits"),
                "variant": t["variant"],
                "steps": len(t["steps"]),
                "end_reason": t["end_reason"],
                "file": "%s.json" % t["persona"]["id"],
            }
            for t in traces
        ],
    }
    if extra:
        payload.update(extra)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=1)
    return path
