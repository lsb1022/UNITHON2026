"""프론트 데모용 데이터를 TS 파일로 내보낸다.

    python export_web_mock.py --clean final_clean10 --buggy final_buggy10

백엔드 없이 프론트만으로 "이런 식으로 작동합니다"를 보여주기 위한 것이다.
**숫자를 손으로 적지 않는다** — 실제 실행 기록에서 읽어 `web/src/api/mock-data.ts`
로 내보낸다. 실행을 다시 하면 이 명령만 다시 돌리면 된다.

담기는 것: 프로젝트/테스트 카드에 쓸 요약, 페르소나 분포, 실측 비용·토큰,
그리고 실행 화면이 흉내 낼 진행률의 근거(사람별 스텝 수와 결과).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:  # noqa: BLE001
        pass

WEB_OUT = os.path.join("..", "web", "src", "api", "mock-data.ts")
END_LABEL = {"goal_reached": "달성",
             # 본인은 달성이라 했지만 근거가 화면에 없던 경우. 달성으로 세지 않는다.
             "claimed_unverified": "근거 없음",
             "gave_up": "포기", "max_steps": "스텝 소진",
             "loop_detected": "맴돌다 중단", "budget_stop": "예산 상한", "error": "오류"}


def persona_book() -> dict:
    """id → 나이·성별. 기록 파일에는 없다.

    나이·성별은 나중에 넣은 값이라 이미 돌린 실행의 기록에는 안 들어 있다.
    사람은 id 로 고정돼 있으므로(P001 은 언제나 P001) 규격 파일에서 이어 붙인다.
    다시 돌리지 않아도 화면이 그 값을 말할 수 있다.
    """
    path = os.path.join("personas", "personas.json")
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as f:
        return {p["id"]: {"age_band": p.get("age_band"), "gender": p.get("gender")}
                for p in json.load(f)["personas"]}


BOOK = None


def load_run(run_id: str) -> dict | None:
    path = os.path.join("logs", run_id, "index.json")
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        idx = json.load(f)
    people = []
    for p in idx["personas"]:
        with open(os.path.join("logs", run_id, p["file"]), encoding="utf-8") as f:
            t = json.load(f)
        first = t["steps"][0]["thought"] if t["steps"] else ""
        last = t["steps"][-1]["thought"] if t["steps"] else ""
        who = (BOOK or {}).get(p["id"], {})
        people.append({
            "age_band": who.get("age_band"),
            "gender": who.get("gender"),
            "journey": journey(t),
            "trail": trail(t),
            # 단계 상세 창이 쓸 원본. 파일로 나갈 때는 떼어낸다 — 통째로
            # 넣으면 mock-data.ts 가 수 MB 가 된다.
            "steps_raw": t["steps"],
            "id": p["id"],
            "label": t["persona"].get("label", ""),
            "traits": t["persona"].get("traits", {}),
            "steps": len(t["steps"]),
            "synthetic": bool(t.get("synthetic")),
            "end": p["end_reason"],
            "endLabel": END_LABEL.get(p["end_reason"], p["end_reason"]),
            "firstThought": first,
            "lastThought": last,
        })
    return {"runId": run_id, "variant": idx.get("variant"),
            "usage": idx.get("usage", {}), "personas": people,
            # 추정으로 부풀린 실행인지. 화면이 그대로 말할 수 있어야 한다 —
            # 실측과 추정이 섞인 걸 숨기면 실측 숫자까지 의심받는다.
            "synthetic": bool(idx.get("synthetic")),
            "measuredCount": idx.get("measured_count"),
            "syntheticCount": idx.get("synthetic_count"),
            "syntheticNote": idx.get("synthetic_note"),
            "usageNote": idx.get("usage_note")}


SCREEN_LABEL = {
    "index.html": "홈", "list.html": "상품 목록", "product.html": "상품 상세",
    "cart.html": "장바구니", "checkout.html": "주문/결제", "complete.html": "주문 완료",
}


def screen_key(url: str) -> str:
    """URL 을 화면 종류로 접는다. ?id=1 과 ?id=7 은 같은 '상품 상세'다.

    남의 사이트는 한글 경로가 퍼센트 인코딩으로 온다
    (`/w/%EC%88%AD%EC%8B%A4...`). 그대로 두면 화면 이름이 암호가 되므로 푼다.
    """
    from urllib.parse import unquote
    # 물음표와 우물정(#) 뒤는 같은 화면 안의 사정이다. 둘 다 떼야
    # '숭실대학교' 와 '숭실대학교#' 가 한 화면으로 묶인다.
    last = url.split("/")[-1].split("?")[0].split("#")[0]
    if not last:
        return "index.html"
    try:
        return unquote(last)
    except Exception:  # noqa: BLE001
        return last


def journey(trace: dict) -> list[str]:
    """한 사람이 지나간 화면 순서. 같은 화면에 연달아 머문 것은 한 번으로 친다."""
    out = []
    for s in trace["steps"]:
        k = screen_key(s["snapshot"]["url"])
        if not out or out[-1] != k:
            out.append(k)
    return out


def trail(trace: dict) -> list[str]:
    """스텝마다 어느 화면에 있었나. `journey` 와 달리 **접지 않는다**.

    같은 화면에 세 번 머물렀으면 세 칸이 된다. 흐름도에서 "여기 붙잡혀 있었다"가
    보여야 하는데, 접어버리면 그 정체가 사라진다.
    """
    return [screen_key(s["snapshot"]["url"]) for s in trace["steps"]]


def persona_rows(primary: dict, control: dict | None) -> dict:
    """페르소나별 결과 비교 표 (피그마 '페르소나별 결과 비교').

    같은 사람이 정상판과 결함판에서 어떻게 달라졌는지가 이 표의 전부다.
    한쪽만 보면 "이 사람이 못한 게 사이트 탓인지 역량 탓인지" 알 수 없다.
    """
    base = {p["id"]: p for p in (control or {}).get("personas", [])}
    rows = []
    for p in primary["personas"]:
        b = base.get(p["id"])
        ok = lambda x: x and x["end"] == "goal_reached"          # noqa: E731
        changed = bool(b) and ok(b) != ok(p)
        rows.append({
            "id": p["id"], "code": p["id"], "name": p["label"],
            "traits": p.get("traits") or {},
            "age_band_real": p.get("age_band"), "gender_real": p.get("gender"),
            # 화면의 옛 칸(연령대·성별)에도 값을 넣어둔다 — 표가 바뀌기 전까지 빈칸이 되지 않도록.
            "age_band": p["label"], "gender": "",
            "outcome": "success" if ok(p) else "drop",
            "step_count": p["steps"],
            "baseline": None if not b else {
                "outcome": "success" if ok(b) else "drop",
                "end_label": b["endLabel"], "step_count": b["steps"],
            },
            "compare": {"outcome": "success" if ok(p) else "drop",
                        "end_label": p["endLabel"], "step_count": p["steps"]},
            "changed": changed,
        })
    exhausted = sum(1 for p in primary["personas"] if p["end"] == "max_steps")
    return {
        "total": len(rows),
        "changed": sum(1 for r in rows if r["changed"]),
        "exhausted": exhausted,
        "baseline_run": (control or {}).get("runId"),
        "compare_run": primary.get("runId"),
        "axes": {"literacy": "숙련도", "attention": "주의 지속",
                 "patience": "인내심", "breadth": "탐색 범위"},
        "items": rows,
    }


def build_views(run: dict, control: dict | None = None) -> dict:
    """결과 화면이 묻는 네 가지에 우리 기록으로 답한다.

    화면(TestDetailPage)은 이미 만들어져 있고 데이터만 없었다. 없는 숫자를
    지어내지 않고 logs/ 에서 그대로 뽑는다.
    """
    people = run["personas"]
    n = len(people) or 1
    ok = [p for p in people if p["end"] == "goal_reached"]
    drop = [p for p in people if p["end"] != "goal_reached"]

    # ── 경로 카드: 같은 화면 순서를 걸어간 사람끼리 묶는다 ──────────
    from collections import defaultdict
    groups = defaultdict(list)
    for p in people:
        groups[tuple(p["journey"])].append(p)

    def cards(sel, kind):
        rows = []
        for path, members in groups.items():
            mine = [m for m in members if (m["end"] == "goal_reached") == (kind == "success")]
            if not mine:
                continue
            rows.append((path, mine))
        rows.sort(key=lambda r: -len(r[1]))
        out = []
        for i, (path, members) in enumerate(rows[:4], 1):
            shown = list(path[:5])
            out.append({
                "rank": i,
                "name": "경로 %d" % i,
                "label": " → ".join(SCREEN_LABEL.get(k, k) for k in shown),
                "persona_count": len(members),
                "step_count": round(sum(m["steps"] for m in members) / len(members)),
                "screens": [{"key": k, "title": SCREEN_LABEL.get(k, k), "url": None}
                            for k in shown],
                "more": max(0, len(path) - len(shown)),
            })
        return out

    # ── 흐름도: 열 = 몇 번째 스텝, 막대 = 그 스텝에 그 화면에 있던 사람 ────
    #
    # 예전에는 열 하나가 화면 하나였다. 그러면 상품 상세에 세 번 들러도 막대가
    # 하나라 되돌아간 것이 안 보이고, 또 사람마다 같은 화면을 서로 다른 순서에
    # 밟았는데도 같은 자리에 뭉뚱그려진다. 스텝을 열로 세우면 둘 다 살아난다 —
    # "3번째 스텝에 누구는 장바구니, 누구는 아직 상품 목록" 이 바로 보인다.
    #
    # 끝난 사람은 다음 열의 달성/이탈 막대로 흘러들어가 거기서 멈춘다.
    # 그래야 모든 열의 인원 합이 전체 인원과 맞아떨어진다 — 중간에서 사람이
    # 증발하는 흐름도는 읽는 사람을 속인다.
    ORDER = ["index.html", "list.html", "product.html", "cart.html",
             "checkout.html", "complete.html"]
    # 모든 스텝을 다 그리면 가로로만 길어진다. 30이면 지금까지의 기록은
    # 한 명도 안 잘리고(최장 24스텝), 그보다 긴 실행은 잘린 인원을 밝힌다.
    MAX_COLUMNS = 30

    nodes: dict[str, dict] = {}
    links: dict[tuple[str, str], dict] = {}
    truncated = 0

    def node(col: int, key: str, title: str, rank: int) -> str:
        nid = "c%d:%s" % (col, key)
        nodes.setdefault(nid, {"id": nid, "column": col, "key": key, "title": title,
                               "rank": rank, "count": 0, "success": 0, "drop": 0})
        return nid

    def visit(nid: str, good: bool) -> None:
        d = nodes[nid]
        d["count"] += 1
        d["success" if good else "drop"] += 1

    def link(a: str, b: str, good: bool) -> None:
        d = links.setdefault((a, b), {"source": a, "target": b,
                                      "count": 0, "success": 0, "drop": 0})
        d["count"] += 1
        d["success" if good else "drop"] += 1

    for p in people:
        good = p["end"] == "goal_reached"
        path = p.get("trail") or p["journey"]
        cut = path[:MAX_COLUMNS]
        if len(path) > MAX_COLUMNS:
            truncated += 1

        prev = None
        for col, key in enumerate(cut):
            rank = ORDER.index(key) if key in ORDER else len(ORDER)
            nid = node(col, key, SCREEN_LABEL.get(key, key), rank)
            visit(nid, good)
            if prev is not None:
                link(prev, nid, good)
            prev = nid

        # 끝까지 간 사람만 마지막 막대로 보낸다. 잘린 사람은 어떻게 끝났는지
        # 이 그림 안에서 알 수 없으므로 달성했다고도 이탈했다고도 말하지 않는다.
        if prev is not None and len(path) <= MAX_COLUMNS:
            key = "end_goal" if good else "end_drop"
            nid = node(len(cut), key, "달성" if good else "이탈",
                       len(ORDER) + (1 if good else 2))
            visit(nid, good)
            link(prev, nid, good)

    columns: dict[int, list] = {}
    for d in nodes.values():
        columns.setdefault(d["column"], []).append(d)
    for col in columns.values():
        # 같은 화면을 열마다 같은 높이에 두어야 띠가 가로로 흘러 읽힌다.
        col.sort(key=lambda d: (d["rank"], d["key"]))
        for d in col:
            d.pop("rank")

    diagram = {
        "columns": [{"index": i, "label": "%d단계" % (i + 1), "nodes": columns[i]}
                    for i in sorted(columns)],
        "links": list(links.values()),
        "total": len(people),
        "truncated": truncated,
        "max_columns": MAX_COLUMNS,
    }

    # ── 단계 상세: 막대를 누르면 뜨는 창 (Figma 290:11203 / 290:11542) ──
    #
    # 화면 사진 위에 그 화면에서 눌린 자리를 얹고, 그 순간 그 자리에 있던
    # 사람들의 속마음을 옆에 세운다. 스크린샷은 답사자가 한 번 찍어둔 화면
    # 6종을 재사용한다 — 페르소나마다 다시 찍지 않는 것이 이 파이프라인의
    # 설계다(뒷사람은 글로만 움직인다). 좌표는 페이지 절대좌표라 그대로 겹친다.
    shots = {}
    shot_index = os.path.join("..", "web", "public", "screens", "index.json")
    if os.path.exists(shot_index):
        with open(shot_index, encoding="utf-8") as f:
            for var, entries in json.load(f).items():
                shots[var] = {e["key"]: e for e in entries}
    variant = run.get("variant") or "buggy"
    sheet = shots.get(variant, {})

    def shot_of(key: str) -> dict | None:
        e = sheet.get(key)
        if not e:
            return None
        return {"src": "/screens/" + e["file"], "w": e["w"], "h": e["h"]}

    # 화면별 전체 클릭 — 한 단계에 3~6번뿐이라 그것만으로는 열지도가 되지 않는다.
    # 그 화면에서 벌어진 일 전부를 옅게 깔고, 이 단계의 클릭만 진하게 얹는다.
    screen_clicks: dict[str, list] = {}
    for p in people:
        for s in p["steps_raw"]:
            r = s.get("resolved")
            if not r:
                continue
            key = screen_key(s["snapshot"]["url"])
            screen_clicks.setdefault(key, []).append({
                "x": round(r["x"] + r["w"] / 2), "y": round(r["y"] + r["h"] / 2),
                "wasted": not (s.get("outcome") or {}).get("changed"),
            })

    def moment(p: dict, s: dict, extra: dict) -> dict:
        """그 스텝에 이 사람이 무엇을 하고 있었나. 이 창의 알맹이다."""
        r = s.get("resolved") or {}
        return {
            "id": p["id"], "label": p["label"], "traits": p.get("traits") or {},
            "age_band": p.get("age_band"), "gender": p.get("gender"),
            "outcome": "success" if p["end"] == "goal_reached" else "drop",
            "end_label": p["endLabel"], "total_steps": p["steps"],
            # 그 순간 이 사람이 무슨 생각으로 그것을 눌렀는지.
            "thought": s.get("thought", ""),
            "action": (s.get("action") or {}).get("type", ""),
            "target": (r.get("text") or "")[:30],
            "blocked": bool(s.get("blocked_action")),
            **extra,
        }

    steps_detail = {}
    for col in diagram["columns"]:
        for nd in col["nodes"]:
            if nd["key"].startswith("end_"):
                continue
            step_no = nd["column"]
            hits, here, elsewhere, finished = [], [], [], []
            for p in people:
                raw = p["steps_raw"]
                # ① 이미 끝난 사람. 창에서 빼버리면 "10단계에 왜 6명뿐이지?"가 된다.
                if step_no >= len(raw):
                    finished.append({
                        "id": p["id"], "label": p["label"], "traits": p.get("traits") or {},
                        "age_band": p.get("age_band"), "gender": p.get("gender"),
                        "outcome": "success" if p["end"] == "goal_reached" else "drop",
                        "end_label": p["endLabel"], "total_steps": p["steps"],
                        "thought": (raw[-1].get("thought", "") if raw else ""),
                        "action": "", "target": "", "blocked": False,
                    })
                    continue
                s = raw[step_no]
                key = screen_key(s["snapshot"]["url"])
                # ② 같은 단계, 다른 화면. 같은 시각에 무리가 어떻게 갈렸는지가 보인다.
                if key != nd["key"]:
                    elsewhere.append(moment(p, s, {
                        "screen": key, "screen_title": SCREEN_LABEL.get(key, key)}))
                    continue
                # ③ 이 화면에 있던 사람
                r = s.get("resolved")
                if r:
                    hits.append({
                        "x": round(r["x"] + r["w"] / 2), "y": round(r["y"] + r["h"] / 2),
                        "w": round(r["w"]), "h": round(r["h"]),
                        "label": (r.get("text") or "").strip()[:24],
                        "wasted": not (s.get("outcome") or {}).get("changed"),
                        "persona": p["id"],
                    })
                here.append(moment(p, s, {}))
            steps_detail[nd["id"]] = {
                "id": nd["id"], "step": step_no + 1, "screen": nd["key"],
                "title": SCREEN_LABEL.get(nd["key"], nd["key"]),
                "count": nd["count"], "shot": shot_of(nd["key"]),
                "clicks": hits, "screen_clicks": screen_clicks.get(nd["key"], []),
                "wasted": sum(1 for h in hits if h["wasted"]),
                "personas": here,
                # 이 셋을 더하면 언제나 전체 인원이다. 그래야 창이 거짓말을 하지 않는다.
                "elsewhere": elsewhere,
                "finished": finished,
                "total": len(people),
            }

    # 아래 필름 띠. 단계마다 가장 많은 사람이 있던 화면을 대표로 세운다.
    filmstrip = []
    for col in diagram["columns"]:
        real = [n for n in col["nodes"] if not n["key"].startswith("end_")]
        if not real:
            continue
        top = max(real, key=lambda n: n["count"])
        filmstrip.append({"step": top["column"] + 1, "id": top["id"],
                          "title": top["title"], "count": top["count"],
                          "shot": shot_of(top["key"]),
                          "others": len(real) - 1})


    # ── 페르소나 표 ────────────────────────────────────────────────
    # 화면의 칸 이름은 연령대·성별이지만 우리 페르소나는 특성 축으로 나뉜다.
    # 없는 값을 지어내지 않고 있는 것을 넣는다 (칸 이름은 화면에서 고칠 몫).
    axis_short = {"literacy": "숙련", "attention": "주의",
                  "patience": "인내", "breadth": "탐색"}
    rows = []
    for p in people:
        t = p.get("traits") or {}
        rows.append({
            "id": p["id"], "code": p["id"], "name": p["label"],
            "age_band": "숙련 %s · 주의 %s" % (t.get("literacy", "-"), t.get("attention", "-")),
            "gender": "인내 %s · 탐색 %s" % (t.get("patience", "-"), t.get("breadth", "-")),
            "outcome": "success" if p["end"] == "goal_reached" else "drop",
            "step_count": p["steps"],
        })

    # ── 재생: 한 사람의 여정을 처음부터 끝까지 ────────────────────
    #
    # 단계 상세 창은 "이 순간 여기 있던 사람들"을 가로로 본다. 재생은 반대로
    # **한 사람을 세로로** 따라간다 — 어디서 헤맸고 언제 포기했는지는 그 사람의
    # 스텝을 이어서 봐야 보인다.
    #
    # 화면마다 사진 한 장을 쓰고, 그 사람이 그 스텝에 있던 스크롤 위치와 누른
    # 자리를 함께 싣는다. 그러면 화면은 사진을 그 위치로 밀고 표시만 얹으면 된다.
    replay = {}
    for p in people:
        frames = []
        for i, s in enumerate(p["steps_raw"]):
            key = screen_key(s["snapshot"]["url"])
            r = s.get("resolved") or {}
            snap = s["snapshot"]
            frames.append({
                "step": i + 1,
                "screen": key,
                "title": SCREEN_LABEL.get(key, key),
                "shot": shot_of(key),
                "scroll_y": snap.get("scroll_y") or 0,
                "viewport": snap.get("viewport") or {"w": 1280, "h": 800},
                "thought": s.get("thought", ""),
                "action": (s.get("action") or {}).get("type", ""),
                "target": (r.get("text") or "")[:30],
                # 누른 자리(페이지 절대좌표). 없으면 표시할 것이 없다.
                "box": ({"x": round(r["x"]), "y": round(r["y"]),
                         "w": round(r["w"]), "h": round(r["h"])} if r else None),
                "changed": bool((s.get("outcome") or {}).get("changed")),
                "note": (s.get("outcome") or {}).get("note") or "",
                "blocked": bool(s.get("blocked_action")),
                "elapsed_ms": s.get("elapsed_ms"),
            })
        replay[p["id"]] = {
            "id": p["id"], "label": p["label"], "traits": p.get("traits") or {},
            "age_band": p.get("age_band"), "gender": p.get("gender"),
            "outcome": "success" if p["end"] == "goal_reached" else "drop",
            "end_label": p["endLabel"], "steps": len(frames),
            "synthetic": bool(p.get("synthetic")),
            "frames": frames,
        }

    return {
        "detail": {
            "synthetic": bool(run.get("synthetic")),
            "measured_count": run.get("measuredCount"),
            "synthetic_count": run.get("syntheticCount"),
            "synthetic_note": run.get("syntheticNote"),
            "persona_total": len(people),
            "journey_count": len(people),
            "success_rate": round(len(ok) / n * 100, 1),
            "drop_rate": round(len(drop) / n * 100, 1),
            "avg_success_steps": round(sum(p["steps"] for p in ok) / len(ok), 1) if ok else None,
        },
        "paths": {
            "total": len(people),
            "success": {"count": len(ok), "percent": round(len(ok) / n * 100, 1)},
            "drop": {"count": len(drop), "percent": round(len(drop) / n * 100, 1)},
            "paths": {"success": cards(ok, "success"), "drop": cards(drop, "drop")},
        },
        "diagram": diagram,
        "steps": steps_detail,
        "replay": replay,
        "filmstrip": filmstrip,
        "personas": persona_rows(run, control),
    }


def persona_sentences() -> dict:
    """페르소나 규격의 축별 문장표. 화면의 '성격' 칸은 이것을 이어 붙인 것이다."""
    try:
        from uxagent import persona
    except Exception:  # noqa: BLE001
        return {}
    return {axis: {str(level): text for level, text in levels.items()}
            for axis, levels in persona.SENTENCES.items()}


def load_map(variant: str) -> dict:
    path = os.path.join("maps", "site_map_%s.json" % variant)
    meta = os.path.join("maps", "survey_meta_%s.json" % variant)
    out = {"pages": [], "steps": 0, "shots": 0, "usd": 0.0}
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            m = json.load(f)
        out["pages"] = [{"path": p["path"], "title": p["title"], "layout": p["layout"]}
                        for p in m["pages"]]
    if os.path.exists(meta):
        with open(meta, encoding="utf-8") as f:
            mm = json.load(f)
        out["steps"] = mm.get("steps", 0)
        out["shots"] = mm.get("screenshots", 0)
        out["usd"] = (mm.get("usage") or {}).get("cost_usd", 0)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="프론트 데모용 데이터 내보내기")
    ap.add_argument("--clean", default="final_clean10")
    ap.add_argument("--buggy", default="final_buggy10")
    # 우리 테스트베드 말고 다른 사이트를 돌린 기록도 예시로 실을 수 있다.
    #   --site namu=namu_ssu
    ap.add_argument("--site", action="append", default=[],
                    metavar="이름=실행id",
                    help="추가로 실을 실행. 여러 번 쓸 수 있다")
    ap.add_argument("--out", default=WEB_OUT)
    args = ap.parse_args()

    with open(os.path.join("personas", "personas.json"), encoding="utf-8") as f:
        pd = json.load(f)

    global BOOK
    BOOK = persona_book()
    pairs = [("clean", args.clean), ("buggy", args.buggy)]
    for item in args.site:
        if "=" not in item:
            raise SystemExit("--site 는 이름=실행id 꼴이어야 합니다: %s" % item)
        name, rid = item.split("=", 1)
        pairs.append((name.strip(), rid.strip()))
    runs = {k: load_run(v) for k, v in pairs}
    missing = [k for k, v in runs.items() if v is None]
    if missing:
        print("아직 결과가 없는 실행: %s — 있는 것만 내보냅니다." % ", ".join(missing))

    # 페르소나 분포. 프론트는 연령대별 표를 그리지만 우리 축은 특성이다.
    # 거짓 숫자를 만들지 않고 **축 분포를 그대로** 넘긴다. 화면 문구는 프론트가 정한다.
    axes = pd.get("axes", {})
    dist = {a: dict(sorted(Counter(p["traits"][a] for p in pd["personas"]).items()))
            for a in axes}

    # 실측 비용. 추정식이 아니라 우리가 실제로 쓴 값이다.
    per_run = [r["usage"] for r in runs.values() if r]
    calls = sum(u.get("calls", 0) for u in per_run)
    tok_in = sum(u.get("tokens_in", 0) for u in per_run)
    tok_out = sum(u.get("tokens_out", 0) for u in per_run)
    usd = round(sum(u.get("cost_usd", 0) for u in per_run), 4)
    people_n = sum(len(r["personas"]) for r in runs.values() if r) or 1

    # 사람 하나에 스텝 원본이 통째로 달려 있다. 화면은 그것을 직접 읽지 않고
    # views.steps 로 간추린 것만 쓰므로, 파일에 실을 때는 떼어낸다.
    heavy = ("steps_raw", "trail")

    def slim(r: dict) -> dict:
        return {**r, "personas": [{k: v for k, v in p.items() if k not in heavy}
                                  for p in r["personas"]]}

    payload = {
        "generatedAt": pd.get("generated_at"),
        "goal": pd.get("goal"),
        "startPath": pd.get("start_path"),
        "axes": axes,
        "axisDistribution": dist,
        # 성격 문장. 화면이 지어내지 않도록 페르소나 규격의 원문을 그대로 넘긴다.
        "axisSentences": persona_sentences(),

        "personaTotal": len(pd["personas"]),
        "maps": {"clean": load_map("clean"), "buggy": load_map("buggy")},
        "runs": {k: slim(v) for k, v in runs.items() if v},
        # 결과 화면(TestDetailPage)이 묻는 것들을 **두 사이트 기준으로 각각** 만든다.
        # 화면에서 갈아 끼울 수 있어야 "이 막힘이 사이트 탓인가 사람 탓인가"를
        # 같은 자리에서 견줄 수 있다. 서로를 대조군으로 넘겨 페르소나 비교표의
        # 방향도 함께 뒤집힌다.
        # 테스트베드 두 벌은 서로를 대조군으로 삼는다. 그 외 사이트는 짝이 없으므로
        # 대조군 없이 자기 결과만 만든다 — 없는 비교를 지어내지 않는다.
        "viewsByVariant": {
            k: build_views(
                runs[k],
                runs.get("buggy" if k == "clean" else "clean") if k in ("clean", "buggy")
                else None)
            for k in runs if runs.get(k)
        },
        # 기본으로 보여줄 쪽. 결함판이 없으면 정상판을 본다.
        "defaultVariant": "buggy" if runs.get("buggy") else "clean",
        "measured": {
            "calls": calls, "tokensIn": tok_in, "tokensOut": tok_out, "usd": usd,
            "usdPerPersona": round(usd / people_n, 4) if people_n else 0,
            "note": "실제 실행에서 측정한 값입니다. 추정식이 아닙니다.",
        },
    }

    body = ("// 이 파일은 손으로 고치지 않습니다.\n"
            "// agent-ux/export_web_mock.py 가 실제 실행 기록에서 뽑아 씁니다.\n"
            "//   python export_web_mock.py --clean <run_id> --buggy <run_id>\n\n"
            "export const MOCK_DATA = %s\n" % json.dumps(payload, ensure_ascii=False, indent=2))
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8", newline="\n") as f:
        f.write(body)
    print("저장: %s  (%.0fKB)" % (args.out, os.path.getsize(args.out) / 1024))
    for k, r in runs.items():
        if r:
            c = Counter(p["end"] for p in r["personas"])
            print("  %-6s %d명  %s" % (k, len(r["personas"]),
                                      "  ".join("%s %d" % (END_LABEL.get(x, x), n)
                                                for x, n in c.items())))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
