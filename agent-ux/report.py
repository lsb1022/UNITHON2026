"""실행 결과를 문서로 뽑는다 — 두 실행을 나란히 놓고 비교한다.

    python report.py real_buggy_3 real_buggy_scan
    python report.py real_clean_6 real_buggy_3 --out 결과.md
    python report.py real_clean_6                      # 한 실행만

손으로 쓰지 않는 이유: 4회 본실행 뒤에 또 써야 하고, 손으로 쓰면 그때마다
숫자를 옮겨 적다 틀린다. 기록에서 직접 읽어 만든다.

이 도구는 **판정하지 않는다.** 무엇이 결함인지는 정답지(DEFECTS.md)와
대조하는 별개 단계의 일이다. 여기서는 일어난 일만 센다.
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

from uxagent import config

END_LABEL = {
    "goal_reached": "목표 달성", "gave_up": "포기", "max_steps": "스텝 소진",
    "loop_detected": "맴돌다 중단", "budget_stop": "예산 상한", "error": "오류",
}
ACT = {"click": "누름", "type": "입력", "select": "선택", "scroll": "스크롤",
       "back": "뒤로", "goto": "주소 이동", "wait": "기다림",
       "done": "달성 선언", "give_up": "포기"}


def load(run_id: str, log_root: str = "logs") -> dict:
    d = os.path.join(log_root, run_id)
    with open(os.path.join(d, "index.json"), encoding="utf-8") as f:
        idx = json.load(f)
    traces = []
    for p in idx["personas"]:
        with open(os.path.join(d, p["file"]), encoding="utf-8") as f:
            traces.append(json.load(f))
    return {"index": idx, "traces": traces, "run_id": run_id}


def stats(run: dict) -> dict:
    tr = run["traces"]
    steps = [s for t in tr for s in t["steps"]]
    fails = [s for s in steps
             if not (s.get("outcome") or {}).get("changed")
             and s["action"]["type"] not in ("done", "give_up", "wait")]
    blocked = [s for s in steps
               if "덮고 있어" in ((s.get("outcome") or {}).get("note") or "")]
    return {
        "명": len(tr),
        "달성": sum(1 for t in tr if t["end_reason"] == "goal_reached"),
        "포기": sum(1 for t in tr if t["end_reason"] == "gave_up"),
        "총 스텝": len(steps),
        "평균 스텝": round(len(steps) / len(tr), 1) if tr else 0,
        "반응 없던 행동": len(fails),
        "가려져 못 누른 행동": len(blocked),
        "설명서에 없던 화면": sum(1 for s in steps if s.get("map_miss")),
        "막힌 행동": sum(1 for s in steps if s.get("blocked_action")),
    }


def screen_worst(run: dict) -> list[tuple]:
    """화면별 최악 측정값. 어느 화면이 험했는지 한눈에 본다."""
    by = {}
    for t in run["traces"]:
        for s in t["steps"]:
            snap = s["snapshot"]
            key = snap["url"].split("/")[-1].split("?")[0] or "index.html"
            els = snap["elements"]
            row = by.setdefault(key, {"방문": 0, "가려짐": 0, "저대비": 0, "키보드불가": 0})
            row["방문"] += 1
            row["가려짐"] = max(row["가려짐"], sum(1 for e in els if e["occluded"]))
            row["저대비"] = max(row["저대비"], sum(
                1 for e in els if (e.get("contrast") or 99) < 3.0 and not e.get("disabled_attr")))
            row["키보드불가"] = max(row["키보드불가"],
                                sum(1 for e in els if not e["keyboard_reachable"]))
    return sorted(by.items(), key=lambda kv: -kv[1]["가려짐"] - kv[1]["저대비"])


def quotes(run: dict, limit: int = 6) -> list[str]:
    """마지막 생각 — 왜 그만뒀는지가 가장 많은 것을 말한다."""
    out = []
    for t in run["traces"]:
        if not t["steps"]:
            continue
        last = t["steps"][-1]
        out.append("- **%s** (%s, %d스텝) — %s"
                   % (t["persona"]["id"], END_LABEL.get(t["end_reason"], t["end_reason"]),
                      len(t["steps"]), last["thought"]))
    return out[:limit]


def md_table(rows: list[tuple], headers: list[str]) -> list[str]:
    out = ["| " + " | ".join(headers) + " |",
           "|" + "|".join(["---"] * len(headers)) + "|"]
    for r in rows:
        out.append("| " + " | ".join(str(x) for x in r) + " |")
    return out


def build(runs: list[dict]) -> str:
    L = []
    L.append("# 페르소나 실행 결과")
    L.append("")
    ids = " / ".join(r["run_id"] for r in runs)
    L.append("실행: `%s`" % ids)
    L.append("")
    L.append("이 문서는 `report.py` 가 기록에서 직접 읽어 만든 것이다. "
             "무엇이 결함인지는 판정하지 않는다 — 일어난 일만 센다.")
    L.append("")

    # 1. 요약
    L.append("## 한눈에")
    L.append("")
    keys = list(stats(runs[0]).keys())
    headers = ["항목"] + [r["run_id"] for r in runs]
    rows = []
    for k in keys:
        rows.append([k] + [stats(r)[k] for r in runs])
    L += md_table(rows, headers)
    L.append("")

    # 2. 사람별
    for r in runs:
        L.append("## %s — 사람별" % r["run_id"])
        L.append("")
        idx = r["index"]
        rows = []
        for t in r["traces"]:
            p = t["persona"]
            rows.append([p["id"], p.get("label", ""), p["goal"][:28],
                         "%dms" % p["dwell_ms"],
                         END_LABEL.get(t["end_reason"], t["end_reason"]),
                         len(t["steps"])])
        L += md_table(rows, ["ID", "성격", "목표", "체류", "결과", "스텝"])
        L.append("")
        u = idx.get("usage", {})
        if u:
            L.append("호출 %s회 / 입력 %s · 출력 %s 토큰 / 약 $%s"
                     % (u.get("calls"), u.get("tokens_in"), u.get("tokens_out"),
                        u.get("cost_usd")))
            L.append("")

    # 3. 화면별 측정값
    for r in runs:
        L.append("## %s — 화면별 최악 측정값" % r["run_id"])
        L.append("")
        L.append("코드가 잰 값이다. 스크린샷을 본 모델이 말한 것이 아니다.")
        L.append("")
        rows = [[k, v["방문"], v["가려짐"], v["저대비"], v["키보드불가"]]
                for k, v in screen_worst(r)]
        L += md_table(rows, ["화면", "방문 횟수", "가려짐", "저대비", "키보드 불가"])
        L.append("")

    # 4. 마지막 생각
    for r in runs:
        L.append("## %s — 각자의 마지막 생각" % r["run_id"])
        L.append("")
        L.append("포기가 몰린 자리가 진짜 마찰 지점이다.")
        L.append("")
        L += quotes(r)
        L.append("")

    # 5. 재현 방법
    L.append("## 다시 만들려면")
    L.append("")
    L.append("```bash")
    for r in runs:
        idx = r["index"]
        L.append("python run.py --variant %s --run-id %s%s"
                 % (idx.get("variant", "?"), r["run_id"],
                    "" if idx.get("map_used", True) else " --no-map"))
    L.append("python report.py %s" % " ".join(r["run_id"] for r in runs))
    L.append("```")
    L.append("")
    L.append("기록 원본은 `logs/{run_id}/P0xx.json`, 사람이 읽는 형태는 "
             "`python diary.py <파일>`.")
    return "\n".join(L)


def main() -> int:
    ap = argparse.ArgumentParser(description="실행 결과 문서 생성")
    ap.add_argument("runs", nargs="+", help="비교할 run_id (logs/ 아래 폴더명)")
    ap.add_argument("--out", default="", help="저장할 파일. 없으면 화면에만 출력")
    args = ap.parse_args()

    runs = []
    for rid in args.runs:
        if not os.path.exists(os.path.join("logs", rid, "index.json")):
            print("그런 실행이 없습니다: logs/%s" % rid)
            return 2
        runs.append(load(rid))

    doc = build(runs)
    if args.out:
        with open(args.out, "w", encoding="utf-8", newline="\n") as f:
            f.write(doc + "\n")
        print("저장: %s (%d줄)" % (args.out, doc.count("\n") + 1))
    else:
        print(doc)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
