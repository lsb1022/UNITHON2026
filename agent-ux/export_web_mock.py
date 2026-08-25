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
END_LABEL = {"goal_reached": "달성", "gave_up": "포기", "max_steps": "스텝 소진",
             "loop_detected": "맴돌다 중단", "budget_stop": "예산 상한", "error": "오류"}


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
        people.append({
            "id": p["id"],
            "label": t["persona"].get("label", ""),
            "traits": t["persona"].get("traits", {}),
            "steps": len(t["steps"]),
            "end": p["end_reason"],
            "endLabel": END_LABEL.get(p["end_reason"], p["end_reason"]),
            "firstThought": first,
            "lastThought": last,
        })
    return {"runId": run_id, "variant": idx.get("variant"),
            "usage": idx.get("usage", {}), "personas": people}


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
    ap.add_argument("--out", default=WEB_OUT)
    args = ap.parse_args()

    with open(os.path.join("personas", "personas.json"), encoding="utf-8") as f:
        pd = json.load(f)

    runs = {k: load_run(v) for k, v in (("clean", args.clean), ("buggy", args.buggy))}
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

    payload = {
        "generatedAt": pd.get("generated_at"),
        "goal": pd.get("goal"),
        "startPath": pd.get("start_path"),
        "axes": axes,
        "axisDistribution": dist,
        "personaTotal": len(pd["personas"]),
        "maps": {"clean": load_map("clean"), "buggy": load_map("buggy")},
        "runs": {k: v for k, v in runs.items() if v},
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
