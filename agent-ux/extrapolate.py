"""실측 몇 명에서 얻은 규칙을 나머지 인원에 적용해 **추정 기록**을 만든다.

    python extrapolate.py --from wiki_all --to wiki30 --count 30

**이것은 측정값이 아니다.** 발표에서 "30명 규모면 이렇게 보인다"를 그림으로
보여주기 위한 것이고, 만들어진 사람마다 `synthetic: true` 가 박힌다. 실행 목록
(index.json)에도 몇 명이 실측이고 몇 명이 추정인지 남는다.

**왜 이 정도는 해도 되는가.** 규칙을 우리가 정하지 않았다. 실측에서 읽어낸다 —
주의 지속 몇 단계에서 몇 명이 달성했고 몇 스텝이 걸렸는지를 그대로 쓴다.
관측이 없는 구간은 만들지 않고 이웃 구간에서 빌려 오며, 그 사실도 적는다.

**속마음은 지어내지 않는다.** 같은 주의 지속 단계의 실측 페르소나가 실제로 한
말을 옮긴다. 없는 말을 만들어 붙이면 그 창이 통째로 거짓이 된다.
"""
from __future__ import annotations

import argparse
import json
import os
import random
import sys
from collections import defaultdict

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:  # noqa: BLE001
        pass

from uxagent import config  # noqa: E402


def load_real(run_id: str) -> list[dict]:
    d = os.path.join("logs", run_id)
    idx = json.load(open(os.path.join(d, "index.json"), encoding="utf-8"))
    out = []
    for p in idx["personas"]:
        out.append(json.load(open(os.path.join(d, p["file"]), encoding="utf-8")))
    return out


def observed(real: list[dict]) -> dict:
    """주의 지속 단계별로 '달성 비율'과 '스텝 수'를 읽어낸다."""
    by = defaultdict(lambda: {"n": 0, "ok": 0, "steps": []})
    for t in real:
        a = t["persona"]["traits"]["attention"]
        r = by[a]
        r["n"] += 1
        r["steps"].append(len(t["steps"]))
        if t["end_reason"] == "goal_reached":
            r["ok"] += 1
    return dict(by)


def nearest(stats: dict, level: int) -> tuple[dict, int | None]:
    """관측이 없는 단계는 가장 가까운 관측 단계에서 빌린다."""
    if level in stats:
        return stats[level], None
    src = min(stats, key=lambda k: (abs(k - level), k))
    return stats[src], src


def rate_of(st: dict, prior: float) -> float:
    """**0% / 100% 로 단정하지 않는다 — 다만 50% 로 끌어당기지도 않는다.**

    한 단계에서 본 사람이 한두 명뿐이라 1명 성공을 "이 단계는 100%" 로 쓰면
    표본 하나를 법칙으로 승격시키는 것이다. 그래서 한 명분을 더한 셈으로
    완화하는데, **어디로 완화하느냐**가 중요하다.

    처음에는 성공·실패를 한 명씩 더해 50% 쪽으로 당겼다. 그러면 실측이 4/6
    (66.7%)인데 만들어진 30명은 53%가 되어, 없던 실패가 늘어난다. 우리가 아는
    가장 좋은 기준선은 50%가 아니라 **이 사이트에서 실제로 나온 전체 비율**이다.
    그쪽으로 당긴다.
    """
    return (st["ok"] + prior) / (st["n"] + 1)


def build(person: dict, stats: dict, real: list[dict], rng: random.Random,
          run_id: str, goal: str, ok: bool, prior: float) -> dict:
    a = person["traits"]["attention"]
    st, borrowed = nearest(stats, a)
    rate = rate_of(st, prior)

    base = rng.choice(st["steps"])
    # ±25% 안에서 흔든다. 전원이 똑같은 스텝 수면 그림이 자로 잰 듯 보인다.
    steps_n = max(3, min(person["max_steps"],
                         int(round(base * rng.uniform(0.75, 1.25)))))

    # 같은 주의 단계의 실측 사람이 실제로 한 말을 빌린다. 없으면 아무나.
    pool = [t for t in real if t["persona"]["traits"]["attention"] == a] or real
    donor = rng.choice(pool)

    steps = []
    for n in range(1, steps_n + 1):
        src = donor["steps"][min(n - 1, len(donor["steps"]) - 1)]
        steps.append({
            "step": n,
            "thought": src["thought"],
            "action": dict(src["action"]),
            "resolved": src.get("resolved"),
            "outcome": dict(src.get("outcome") or {}),
            "snapshot": src["snapshot"],
            "map_slice_used": src.get("map_slice_used", False),
            "map_miss": src.get("map_miss", False),
            "blocked_action": None,
            "elapsed_ms": src.get("elapsed_ms"),
        })
    if steps:
        steps[-1]["action"] = {"type": "done" if ok else "give_up"}
        steps[-1]["outcome"] = {"changed": False,
                                "url_after": steps[-1]["snapshot"]["url"],
                                "note": "목표를 이뤘다고 판단" if ok else "포기"}

    return {
        # 이 표시가 이 파일의 존재 이유다. 지우지 말 것.
        "synthetic": True,
        "synthetic_note": ("실측이 아니라 추정입니다. 주의 지속 %d단계의 실측"
                           "%s에서 달성 비율 %.0f%%(관측 %d/%d 에 라플라스 보정)와 "
                           "스텝 수를 뽑았고, 속마음은 같은 단계의 실측 페르소나가 "
                           "실제로 한 말을 옮긴 것입니다."
                           % (a, "" if borrowed is None else
                              "(관측이 없어 %d단계에서 빌림)" % borrowed,
                              100 * rate, st["ok"], st["n"])),
        "schema": 1,
        "run_id": run_id,
        "variant": "wiki",
        "persona": {**person, "goal": goal},
        "started_at": None,
        "ended_at": None,
        "end_reason": "goal_reached" if ok else "gave_up",
        "note": "",
        "steps": steps,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--from", dest="src", required=True, help="실측 실행 id")
    ap.add_argument("--to", dest="dst", required=True, help="만들 실행 id")
    ap.add_argument("--count", type=int, default=30)
    ap.add_argument("--seed", type=int, default=config.PERSONA_SEED)
    args = ap.parse_args()

    real = load_real(args.src)
    stats = observed(real)
    # 완화의 기준선: 이 사이트에서 실제로 나온 전체 달성 비율.
    prior = sum(1 for x in real if x["end_reason"] == "goal_reached") / len(real)
    goal = real[0]["persona"].get("goal", "")
    done = {t["persona"]["id"] for t in real}

    people = json.load(open(os.path.join(config.PERSONAS_DIR, "personas.json"),
                            encoding="utf-8"))["personas"][:args.count]
    rng = random.Random(args.seed)

    out = os.path.join("logs", args.dst)
    os.makedirs(out, exist_ok=True)

    print("실측에서 읽은 규칙 (주의 지속별):")
    for a in sorted(stats):
        s = stats[a]
        print("  %d단계  달성 %d/%d → 보정 %.0f%%  스텝 %s"
              % (a, s["ok"], s["n"], 100 * rate_of(s, prior), s["steps"]))
    print()

    # **비율대로 정확히 배정한다** — 사람마다 동전을 던지지 않는다.
    # 표본이 한두 명이라 추첨을 하면 "주의 5단계가 4단계보다 성공률이 낮다" 같은
    # 흔들림이 나온다. 그건 사이트의 성질이 아니라 주사위의 성질이고, 발표에서
    # 설명할 수 없는 잡음이다. 여기서 하려는 것은 모의실험이 아니라 **투사**다.
    by_band = defaultdict(list)
    for person in people:
        by_band[person["traits"]["attention"]].append(person)

    verdict = {}
    for a, group in by_band.items():
        st, _ = nearest(stats, a)
        real_here = [t for t in real if t["persona"]["traits"]["attention"] == a]
        quota = round(rate_of(st, prior) * len(group))
        # 실측한 사람의 결과는 그대로 둔다. 남은 자리를 나머지가 채운다.
        for t in real_here:
            verdict[t["persona"]["id"]] = t["end_reason"] == "goal_reached"
        used = sum(1 for t in real_here if t["end_reason"] == "goal_reached")
        rest = [p for p in group if p["id"] not in verdict]
        rng.shuffle(rest)
        for i, p in enumerate(rest):
            verdict[p["id"]] = i < max(0, quota - used)

    traces = []
    for person in people:
        if person["id"] in done:
            t = next(x for x in real if x["persona"]["id"] == person["id"])
        else:
            t = build(person, stats, real, rng, args.dst, goal,
                      verdict[person["id"]], prior)
        traces.append(t)
        json.dump(t, open(os.path.join(out, person["id"] + ".json"), "w",
                          encoding="utf-8"), ensure_ascii=False, indent=1)

    n_syn = sum(1 for t in traces if t.get("synthetic"))
    idx = {
        "run_id": args.dst,
        "variant": "wiki",
        "target_url": "https://ko.wikipedia.org/",
        "target_kind": "url",
        "site_kind": "general",
        # 이 실행이 무엇인지 목록에서 바로 보이게 한다.
        "synthetic": True,
        "measured_from": args.src,
        "measured_count": len(traces) - n_syn,
        "synthetic_count": n_syn,
        "synthetic_note": ("%d명 중 %d명은 실제 실행 기록이고 %d명은 실측에서 얻은 "
                           "비율로 만든 추정입니다. 비용·토큰은 실측 %d명분만 "
                           "집계돼 있습니다."
                           % (len(traces), len(traces) - n_syn, n_syn,
                              len(traces) - n_syn)),
        "usage": json.load(open(os.path.join("logs", args.src, "index.json"),
                                encoding="utf-8")).get("usage", {}),
        "personas": [{"id": t["persona"]["id"], "label": t["persona"].get("label"),
                      "goal": t["persona"].get("goal"),
                      "traits": t["persona"].get("traits"),
                      "variant": t["variant"], "steps": len(t["steps"]),
                      "end_reason": t["end_reason"],
                      "synthetic": bool(t.get("synthetic")),
                      "file": t["persona"]["id"] + ".json"} for t in traces],
    }
    json.dump(idx, open(os.path.join(out, "index.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)

    ok = sum(1 for t in traces if t["end_reason"] == "goal_reached")
    print("만든 실행: logs/%s" % args.dst)
    print("  %d명 (실측 %d + 추정 %d)" % (len(traces), len(traces) - n_syn, n_syn))
    print("  달성 %d / 포기 %d  → 성공률 %.1f%%"
          % (ok, len(traces) - ok, 100 * ok / len(traces)))
    print()
    print("주의 지속별 결과:")
    band = defaultdict(lambda: [0, 0])
    for t in traces:
        b = band[t["persona"]["traits"]["attention"]]
        b[0] += 1
        b[1] += t["end_reason"] == "goal_reached"
    for a in sorted(band):
        n, k = band[a]
        print("  %d단계  %d명 중 달성 %d  (%.0f%%)" % (a, n, k, 100 * k / n))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
