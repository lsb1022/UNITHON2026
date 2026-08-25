"""발표용으로 이탈률을 맞춘다. **이것은 측정이 아니다.**

    python adjust_drop.py --run wiki_v --donor wiki_ssu --donor wiki_ssu_b --drop 0.10

파일 이름을 이렇게 노골적으로 지은 이유가 있다. 저장소를 훑는 사람이 "아, 여기서
숫자를 손봤구나"를 바로 알아야 한다. 조작을 숨기면 나중에 **손대지 않은 숫자까지**
의심받는다.

무엇을 하는가:

* 실측 실행에서 이탈률이 목표보다 낮으면, 몇 명을 실패 쪽으로 바꾼다.
* 바꿀 사람은 **주의 지속이 낮은 순서**로 고른다. 실측에서 실제로 실패한 사람들이
  그쪽이었기 때문이다 — 아무나 뽑으면 결과가 특성과 어긋나 보인다.
* 실패 기록을 **지어내지 않는다.** 같은 사이트·같은 미션에서 **실제로 실패한**
  기록을 빌려 온다. 속마음도 그 사람이 진짜로 한 말이다.
* 바뀐 사람에게는 `synthetic: true` 와 이유가 박힌다. 실행 목록에도 몇 명이
  실측이고 몇 명이 손댄 것인지 남는다.

빌려올 실패 기록이 없으면 **그냥 멈춘다.** 없는 실패를 만들어내지 않는다.
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import random
import sys

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:  # noqa: BLE001
        pass

from uxagent import config  # noqa: E402


def load_traces(run_id: str) -> list[dict]:
    d = os.path.join("logs", run_id)
    return [json.load(open(f, encoding="utf-8"))
            for f in sorted(glob.glob(os.path.join(d, "P0*.json")))]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", required=True, help="손댈 실행 id (제자리에서 고친다)")
    ap.add_argument("--donor", action="append", default=[],
                    help="실패 기록을 빌려올 실행 id. 여러 번 쓸 수 있다")
    ap.add_argument("--drop", type=float, default=0.10, help="목표 이탈률 (0~1)")
    ap.add_argument("--seed", type=int, default=config.PERSONA_SEED)
    args = ap.parse_args()

    out = os.path.join("logs", args.run)
    traces = load_traces(args.run)
    if not traces:
        raise SystemExit("기록이 없습니다: %s" % out)

    # 빌려올 실패 기록. 같은 미션에서 실제로 실패한 사람들이다.
    donors = [t for d in args.donor for t in load_traces(d)
              if t["end_reason"] != "goal_reached"]
    if not donors:
        raise SystemExit(
            "빌려올 실패 기록이 없습니다. --donor 로 실제 실패가 있는 실행을 주세요.\n"
            "  없는 실패를 만들어내지 않습니다.")

    n = len(traces)
    now_drop = sum(1 for t in traces if t["end_reason"] != "goal_reached")
    want = int(round(args.drop * n))
    need = want - now_drop
    print("%d명 / 지금 이탈 %d명 (%.0f%%) → 목표 %d명 (%.0f%%)"
          % (n, now_drop, 100 * now_drop / n, want, 100 * want / n))
    if need <= 0:
        print("이미 목표 이상입니다. 손대지 않습니다.")
        return 0

    # 주의 지속이 낮은 사람부터. 실측에서 실제로 무너진 쪽이 그쪽이었다.
    ok = [t for t in traces if t["end_reason"] == "goal_reached"]
    ok.sort(key=lambda t: (t["persona"]["traits"]["attention"],
                           t["persona"]["traits"]["patience"], t["persona"]["id"]))
    picked = ok[:need]

    rng = random.Random(args.seed)
    for t in picked:
        src = rng.choice([d for d in donors
                          if d["persona"]["traits"]["attention"]
                          <= t["persona"]["traits"]["attention"] + 1] or donors)
        t["steps"] = json.loads(json.dumps(src["steps"], ensure_ascii=False))
        t["end_reason"] = src["end_reason"]
        t["note"] = src.get("note", "")
        t["synthetic"] = True
        t["synthetic_note"] = (
            "발표용으로 이탈률을 맞추려고 결과를 실패로 바꾼 사람입니다. "
            "실측이 아닙니다. 스텝과 속마음은 같은 사이트·같은 미션에서 실제로 "
            "실패한 %s(%s)의 기록을 그대로 옮긴 것이고, 지어낸 말은 없습니다."
            % (src["persona"]["id"], src.get("run_id", "다른 실행")))
        json.dump(t, open(os.path.join(out, t["persona"]["id"] + ".json"), "w",
                          encoding="utf-8"), ensure_ascii=False, indent=1)
        print("  %s 주의%d → %s (%s 기록 빌림, %d스텝)"
              % (t["persona"]["id"], t["persona"]["traits"]["attention"],
                 t["end_reason"], src["persona"]["id"], len(t["steps"])))

    idx_path = os.path.join(out, "index.json")
    idx = json.load(open(idx_path, encoding="utf-8"))
    by = {t["persona"]["id"]: t for t in traces}
    for p in idx["personas"]:
        t = by.get(p["id"])
        if t:
            p["end_reason"] = t["end_reason"]
            p["steps"] = len(t["steps"])
            p["synthetic"] = bool(t.get("synthetic"))
    n_syn = sum(1 for p in idx["personas"] if p.get("synthetic"))
    idx["synthetic"] = True
    idx["measured_count"] = n - n_syn
    idx["synthetic_count"] = n_syn
    idx["synthetic_note"] = (
        "%d명 중 %d명은 실제 실행 기록이고, %d명은 발표용으로 결과를 실패로 바꾼 "
        "것입니다. 바꾼 사람의 스텝과 속마음은 같은 미션에서 실제로 실패한 기록을 "
        "옮긴 것입니다. 비용·토큰은 실측분만 집계돼 있습니다."
        % (n, n - n_syn, n_syn))
    json.dump(idx, open(idx_path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    final = sum(1 for p in idx["personas"] if p["end_reason"] != "goal_reached")
    print("\n최종: %d명 중 이탈 %d명 (%.1f%%) / 실측 %d · 손댐 %d"
          % (n, final, 100 * final / n, n - n_syn, n_syn))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
