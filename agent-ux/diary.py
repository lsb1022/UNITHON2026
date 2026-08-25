"""탐험 일기 읽기 — 로그를 사람이 읽는 글로 바꿔 터미널에 뿌린다.

    python diary.py                          # 가장 최근 기록 하나
    python diary.py --list                   # 있는 기록 전부 보기
    python diary.py logs/0825_1332_clean/P001.json
    python diary.py logs/scout_clean_0825_1410.json --full

뷰어(viewer/index.html)가 나오기 전까지 쓰는 도구다. 뷰어는 와이어프레임을
그리지만 이쪽은 **무슨 생각을 하며 어디로 갔는지**만 글로 보여준다.

두 종류를 다 읽는다.
  - 답사 페르소나 일기 (`logs/scout_*.json`)   — 설명서를 어떻게 만들었나
  - 탐색 페르소나 기록 (`logs/{run_id}/P0xx.json`) — 목표를 어떻게 좇았나
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import sys

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:  # noqa: BLE001
        pass

END_LABEL = {
    "goal_reached": "목표 달성", "gave_up": "포기", "max_steps": "스텝 소진",
    "loop_detected": "맴돌다 중단", "budget_stop": "예산 상한", "error": "오류",
    "done": "더 볼 곳 없음", "dry": "새 화면이 안 나옴",
}
ACT = {"click": "누름", "type": "입력", "select": "선택", "scroll": "스크롤",
       "back": "뒤로", "goto": "주소 이동", "wait": "기다림",
       "done": "끝냈다고 판단", "give_up": "포기"}


def short(url: str) -> str:
    return url.split("/")[-1] or url


def find_logs() -> list[str]:
    files = glob.glob(os.path.join("logs", "scout_*.json"))
    files += [f for f in glob.glob(os.path.join("logs", "*", "*.json"))
              if not f.endswith("index.json")]
    return sorted(files, key=os.path.getmtime, reverse=True)


def print_scout(d: dict, full: bool) -> None:
    print("=" * 66)
    print("  답사 페르소나 일기 — %s%s" % (d["variant"], "  [모의]" if d.get("mock") else ""))
    print("  %s / %d스텝 / 찾은 화면 %d종 / 스크린샷 %d장"
          % (d["generated_at"], len(d["steps"]), len(d["pages_found"]),
             d.get("screenshots", 0)))
    print("=" * 66)

    here = None
    for s in d["steps"]:
        if s["url"] != here:
            here = s["url"]
            print("\n── %s  (%s)" % (short(here), s.get("title") or ""))
        mark = "  ★ 설명서에 적음" if s.get("recorded") else ""
        print("  %2d. %s%s" % (s["n"], s["thought"], mark))
        tgt = (" " + s["action"]["target"]) if s["action"].get("target") else ""
        val = (' "%s"' % s["action"]["value"]) if s["action"].get("value") else ""
        note = ("   → %s" % s["note"]) if s["note"] and full else ""
        print("      %s%s%s%s" % (ACT.get(s["action"]["type"], s["action"]["type"]),
                                  tgt, val, note))

    print("\n" + "-" * 66)
    print("  끝: %s" % END_LABEL.get(d["stop_reason"], d["stop_reason"]))
    print("  설명서에 들어간 화면: %s"
          % ", ".join(short(p) for p in d["pages_found"]))


def screen_line(snap: dict) -> str:
    els = snap["elements"]
    below = sum(1 for e in els if e["below_fold"])
    occ = sum(1 for e in els if e["occluded"])
    low = sum(1 for e in els
              if (e.get("contrast") or 99) < 3.0 and not e.get("disabled_attr"))
    kb = sum(1 for e in els if not e["keyboard_reachable"])
    bits = ["요소 %d" % len(els), "접힘선아래 %d" % below]
    if occ:
        bits.append("가려짐 %d" % occ)
    if low:
        bits.append("저대비 %d" % low)
    if kb:
        bits.append("키보드불가 %d" % kb)
    return " · ".join(bits)


def print_persona(d: dict, full: bool) -> None:
    p = d["persona"]
    print("=" * 66)
    print("  %s  %s" % (p["id"], p.get("label", "")))
    print("  \"%s\"" % p["prompt"].replace("\n", " / "))
    print("  대상 %s / 시작 %s / 최대 %d스텝 / 체류 %dms%s"
          % (d["variant"], p["start_path"], p["max_steps"], p["dwell_ms"],
             "  [장바구니 %d줄 시딩]" % d["seeded_lines"] if d.get("seeded_lines") else ""))
    print("=" * 66)

    here = None
    for s in d["steps"]:
        snap = s["snapshot"]
        if snap["url"] != here:
            here = snap["url"]
            print("\n── %s  (%s)" % (short(here), snap.get("title") or ""))
            print("   화면: %s" % screen_line(snap))
        print("  %2d. %s" % (s["step"], s["thought"]))
        a = s["action"]
        tgt = (" " + a["target"]) if a.get("target") else ""
        val = (' "%s"' % a["value"]) if a.get("value") else ""
        line = "      %s%s%s" % (ACT.get(a["type"], a["type"]), tgt, val)
        if s.get("blocked_action"):
            line += "   ⨯ 허용되지 않은 행동이라 하지 않음"
        note = (s.get("outcome") or {}).get("note")
        if note and (full or not s.get("blocked_action")):
            line += "   → %s" % note
        if s.get("map_miss"):
            line += "   [설명서에 없는 화면]"
        print(line)
        if full and s.get("resolved"):
            r = s["resolved"]
            print("         (그 순간 위치 x=%s y=%s %sx%s)" % (r["x"], r["y"], r["w"], r["h"]))

    print("\n" + "-" * 66)
    print("  끝: %s — %d스텝%s"
          % (END_LABEL.get(d["end_reason"], d["end_reason"]), len(d["steps"]),
             ("  (%s)" % d["note"]) if d.get("note") else ""))
    misses = sum(1 for s in d["steps"] if s["map_miss"])
    blocked = sum(1 for s in d["steps"] if s["blocked_action"])
    if misses or blocked:
        print("  설명서에 없던 화면 %d회 / 막힌 행동 %d회" % (misses, blocked))


def main() -> int:
    ap = argparse.ArgumentParser(description="탐험 일기 읽기")
    ap.add_argument("path", nargs="?", default="")
    ap.add_argument("--list", action="store_true", help="있는 기록을 나열한다")
    ap.add_argument("--full", action="store_true", help="좌표·실패 사유까지 전부")
    args = ap.parse_args()

    files = find_logs()
    if args.list:
        if not files:
            print("logs/ 에 기록이 없습니다. 먼저 run.py 나 scout.py 를 돌리세요.")
            return 1
        print("최근 기록 %d개:" % len(files))
        for f in files[:20]:
            print("  %s" % f)
        return 0

    path = args.path or (files[0] if files else "")
    if not path:
        print("logs/ 에 기록이 없습니다. 먼저:")
        print("  python scout.py --variant clean --mock --yes")
        print("  python run.py --variant buggy --mock")
        return 1
    if not os.path.exists(path):
        print("그런 파일이 없습니다: %s" % path)
        return 2

    with open(path, encoding="utf-8") as f:
        d = json.load(f)
    if d.get("kind") == "scout":
        print_scout(d, args.full)
    else:
        print_persona(d, args.full)
    print("  파일: %s" % path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
