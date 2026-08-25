"""실행 결과를 한눈에 보는 HTML 로 뽑는다.

    python report_html.py v2_clean10 v2_buggy10 --out 결과.html
    python report_html.py v2_clean10 --out clean.html

report.py 가 글이라면 이쪽은 그림이다. 같은 사람이 두 사이트에서 어떻게
갈렸는지, 특성 값이 결과와 어떻게 맞물리는지를 표 하나로 본다.

숫자는 전부 기록에서 읽는다. 손으로 옮겨 적지 않는다 — 100명으로 늘리면
옮겨 적다 반드시 틀린다.
"""
from __future__ import annotations

import argparse
import html
import json
import os
import sys
from collections import Counter

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:  # noqa: BLE001
        pass

from uxagent import persona as P

END = {
    "goal_reached": ("달성", "ok"),
    "gave_up": ("포기", "bad"),
    "max_steps": ("스텝 소진", "warn"),
    "loop_detected": ("맴돌다 중단", "warn"),
    "budget_stop": ("예산 상한", "mute"),
    "error": ("오류", "bad"),
}


def load(run_id: str) -> dict:
    d = os.path.join("logs", run_id)
    with open(os.path.join(d, "index.json"), encoding="utf-8") as f:
        idx = json.load(f)
    traces = {}
    for p in idx["personas"]:
        with open(os.path.join(d, p["file"]), encoding="utf-8") as f:
            traces[p["id"]] = json.load(f)
    return {"id": run_id, "index": idx, "traces": traces}


def worst_screen(trace: dict) -> dict:
    occ = low = kb = 0
    for s in trace["steps"]:
        els = s["snapshot"]["elements"]
        occ = max(occ, sum(1 for e in els if e["occluded"]))
        low = max(low, sum(1 for e in els if (e.get("contrast") or 99) < 3.0
                           and not e.get("disabled_attr")))
        kb = max(kb, sum(1 for e in els if not e["keyboard_reachable"]))
    return {"occluded": occ, "low": low, "kb": kb}


def blocked_count(trace: dict) -> int:
    return sum(1 for s in trace["steps"]
               if "덮고 있어" in ((s.get("outcome") or {}).get("note") or ""))


def dots(value: int) -> str:
    """1~5 단계를 점으로. 숫자만 보면 크기가 안 느껴진다."""
    full = "".join('<i class="on"></i>' for _ in range(value))
    rest = "".join("<i></i>" for _ in range(5 - value))
    return '<span class="dots" title="%d단계">%s%s</span>' % (value, full, rest)


def bar(steps: int, cap: int, cls: str) -> str:
    pct = max(4, round(steps / max(cap, 1) * 100))
    return ('<span class="bar %s"><i style="width:%d%%"></i>'
            '<b>%d</b></span>' % (cls, pct, steps))


def build(runs: list[dict], goal: str) -> str:
    ids = sorted(runs[0]["traces"])
    src = {p["id"]: p for p in
           json.load(open(os.path.join("personas", "personas.json"),
                          encoding="utf-8"))["personas"]}
    cap = max(len(t["steps"]) for r in runs for t in r["traces"].values())

    # ── 요약 숫자 ────────────────────────────────────────────
    cards = []
    for r in runs:
        n = len(r["traces"])
        got = sum(1 for t in r["traces"].values() if t["end_reason"] == "goal_reached")
        avg = sum(len(t["steps"]) for t in r["traces"].values()) / n
        u = r["index"].get("usage", {})
        cards.append(
            '<div class="card"><h3>%s</h3>'
            '<p class="big"><b>%d</b><span>/%d 달성</span></p>'
            '<p class="sub">평균 %.1f스텝 · 호출 %s회 · $%s</p></div>'
            % (html.escape(r["id"]), got, n, avg, u.get("calls", "?"),
               u.get("cost_usd", "?")))

    # ── 사람별 표 ────────────────────────────────────────────
    rows = []
    for pid in ids:
        q = src.get(pid, {})
        tr = q.get("traits", {})
        cells = ["".join('<td class="axis">%s</td>' % dots(tr.get(a, 0))
                         for a in P.AXES)]
        flip = None
        outs = []
        for r in runs:
            t = r["traces"].get(pid)
            if not t:
                outs.append('<td colspan="2">—</td>')
                continue
            label, cls = END.get(t["end_reason"], (t["end_reason"], "mute"))
            outs.append('<td><span class="pill %s">%s</span></td>'
                        '<td class="barcell">%s</td>'
                        % (cls, label, bar(len(t["steps"]), cap, cls)))
        if len(runs) == 2:
            a = runs[0]["traces"][pid]["end_reason"] == "goal_reached"
            b = runs[1]["traces"][pid]["end_reason"] == "goal_reached"
            flip = "flip" if (a and not b) else ("keep" if (a and b) else "")
        rows.append('<tr class="%s"><td class="pid">%s</td>%s%s</tr>'
                    % (flip or "", pid, "".join(cells), "".join(outs)))

    # ── 축별 묶음 (낮음 1-2 / 높음 4-5) ────────────────────────
    bands = []
    for a in P.AXES:
        line = ['<tr><th>%s</th>' % P.AXIS_LABEL[a]]
        for r in runs:
            for want in ("low", "high"):
                sel = [t for pid, t in r["traces"].items()
                       if src.get(pid, {}).get("bands", {}).get(a) == want]
                got = sum(1 for t in sel if t["end_reason"] == "goal_reached")
                line.append('<td>%s</td>' % ("%d/%d" % (got, len(sel)) if sel else "—"))
        bands.append("".join(line) + "</tr>")

    # ── 눈에 띄는 사람 ────────────────────────────────────────
    notes = []
    if len(runs) == 2:
        for pid in ids:
            a, b = runs[0]["traces"][pid], runs[1]["traces"][pid]
            if a["end_reason"] == "goal_reached" and b["end_reason"] != "goal_reached":
                w = worst_screen(b)
                notes.append(
                    '<li><b>%s</b> <span class="mono">%s</span> — %s에서는 '
                    '%d스텝에 해냈지만 %s에서는 %s. 화면이 가장 험할 때 '
                    '<span class="mono">가려짐 %d · 저대비 %d · 키보드불가 %d</span>, '
                    '팝업에 막힌 클릭 %d회.<blockquote>%s</blockquote></li>'
                    % (pid, html.escape(src[pid]["label"]), runs[0]["id"],
                       len(a["steps"]), runs[1]["id"],
                       END.get(b["end_reason"], (b["end_reason"],))[0],
                       w["occluded"], w["low"], w["kb"], blocked_count(b),
                       html.escape(b["steps"][-1]["thought"])))

    head = "".join('<th colspan="2">%s</th>' % html.escape(r["id"]) for r in runs)
    band_head = "".join('<th>%s<br><span class="mute">낮음(1-2)</span></th>'
                        '<th>%s<br><span class="mute">높음(4-5)</span></th>'
                        % (html.escape(r["id"]), html.escape(r["id"])) for r in runs)

    fields = {
        "goal": html.escape(goal),
        "cards": "".join(cards),
        "head": head,
        "rows": "".join(rows),
        "band_head": band_head,
        "bands": "".join(bands),
        "notes": "".join(notes) or "<li>뒤집힌 사람이 없습니다.</li>",
        "axes": "".join("<th>%s</th>" % P.AXIS_LABEL[a] for a in P.AXES),
    }
    # CSS 에 % 가 많아 파이썬 포맷을 쓸 수 없다. 자리표시자만 바꿔 넣는다.
    doc = TEMPLATE
    for k, v in fields.items():
        doc = doc.replace("{{%s}}" % k, v)
    return doc


TEMPLATE = """<title>페르소나 실행 결과</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&family=IBM+Plex+Sans+KR:wght@400;500;600;700&display=swap">
<style>
:root{
  --bg:#F2F4F6; --card:#FFFFFF; --ink:#141A21; --soft:#4A5765; --mute:#7C8896;
  --line:#DEE3E8; --line2:#EDF0F3;
  --ok:#1F7A5A; --ok-bg:#E3F2EB; --bad:#A63A2B; --bad-bg:#F8E7E3;
  --warn:#8A5A12; --warn-bg:#F7EEDD; --accent:#0F5C7A; --accent-bg:#E2EEF4;
  --f:"IBM Plex Sans KR",system-ui,"Malgun Gothic",sans-serif;
  --m:"IBM Plex Mono",ui-monospace,monospace;
}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){
  --bg:#0E1319; --card:#161C24; --ink:#E6EBF0; --soft:#AEB9C5; --mute:#7F8B98;
  --line:#28313B; --line2:#1E252E;
  --ok:#6DBF9C; --ok-bg:#152A22; --bad:#DE8B7A; --bad-bg:#2E1E1A;
  --warn:#D6AC66; --warn-bg:#2B2416; --accent:#69B4D6; --accent-bg:#12303D;
}}
:root[data-theme="dark"]{
  --bg:#0E1319; --card:#161C24; --ink:#E6EBF0; --soft:#AEB9C5; --mute:#7F8B98;
  --line:#28313B; --line2:#1E252E;
  --ok:#6DBF9C; --ok-bg:#152A22; --bad:#DE8B7A; --bad-bg:#2E1E1A;
  --warn:#D6AC66; --warn-bg:#2B2416; --accent:#69B4D6; --accent-bg:#12303D;
}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font-family:var(--f);
  line-height:1.6;-webkit-font-smoothing:antialiased}
.wrap{max-width:70rem;margin:0 auto;padding:clamp(1.2rem,4vw,2.8rem)}
h1{font-size:clamp(1.5rem,4vw,2.1rem);font-weight:700;margin:0 0 .3rem;letter-spacing:-.01em}
.goal{font-family:var(--m);font-size:.9rem;color:var(--accent);
  background:var(--accent-bg);display:inline-block;padding:.3rem .7rem;border-radius:3px;
  margin-bottom:1.6rem}
h2{font-size:1.05rem;font-weight:600;margin:2.4rem 0 .5rem}
h2 + p{margin:0 0 1rem;color:var(--soft);font-size:.9rem;max-width:60ch}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(13rem,1fr));gap:.9rem}
.card{background:var(--card);border:1px solid var(--line);border-radius:6px;padding:1rem 1.1rem}
.card h3{margin:0;font-family:var(--m);font-size:.78rem;color:var(--mute);font-weight:400}
.big{margin:.35rem 0 .1rem;font-family:var(--m);font-variant-numeric:tabular-nums}
.big b{font-size:2rem;font-weight:600}
.big span{color:var(--mute);font-size:.95rem;margin-left:.2rem}
.sub{margin:0;font-size:.8rem;color:var(--mute);font-family:var(--m)}
.tablewrap{overflow-x:auto;background:var(--card);border:1px solid var(--line);border-radius:6px}
table{border-collapse:collapse;width:100%;font-size:.86rem;min-width:44rem}
th,td{padding:.5rem .6rem;text-align:left;border-bottom:1px solid var(--line2);white-space:nowrap}
thead th{font-family:var(--m);font-size:.72rem;color:var(--mute);font-weight:400;
  background:var(--bg);position:sticky;top:0}
tbody tr:last-child td{border-bottom:0}
tr.flip{background:var(--bad-bg)}
td.pid{font-family:var(--m);font-weight:600}
td.axis{padding-left:.3rem;padding-right:.3rem}
.dots{display:inline-flex;gap:2px}
.dots i{width:7px;height:7px;border-radius:50%;background:var(--line);display:block}
.dots i.on{background:var(--accent)}
.pill{font-size:.76rem;padding:.12rem .5rem;border-radius:99px;white-space:nowrap}
.pill.ok{color:var(--ok);background:var(--ok-bg)}
.pill.bad{color:var(--bad);background:var(--bad-bg)}
.pill.warn{color:var(--warn);background:var(--warn-bg)}
.pill.mute{color:var(--mute);background:var(--line2)}
.barcell{width:9rem}
.bar{display:flex;align-items:center;gap:.4rem;position:relative}
.bar i{display:block;height:7px;border-radius:99px;background:var(--line);min-width:4px}
.bar.ok i{background:var(--ok)} .bar.bad i{background:var(--bad)}
.bar.warn i{background:var(--warn)}
.bar b{font-family:var(--m);font-size:.76rem;color:var(--mute);font-weight:400;
  font-variant-numeric:tabular-nums}
.mono{font-family:var(--m);font-size:.85em}
.mute{color:var(--mute);font-weight:400}
ul.notes{list-style:none;padding:0;margin:0;display:grid;gap:.8rem}
ul.notes li{background:var(--card);border:1px solid var(--line);border-left:3px solid var(--bad);
  border-radius:6px;padding:.9rem 1.1rem;font-size:.9rem}
blockquote{margin:.5rem 0 0;padding:.5rem .8rem;background:var(--bg);border-radius:4px;
  color:var(--soft);font-size:.86rem}
footer{margin-top:2.5rem;padding-top:1rem;border-top:1px solid var(--line);
  color:var(--mute);font-size:.8rem}
</style>
<div class="wrap">
<h1>페르소나 실행 결과</h1>
<div class="goal">목표 · {{goal}}</div>

<div class="cards">{{cards}}</div>

<h2>사람별 — 같은 목표, 같은 사람, 다른 사이트</h2>
<p>특성은 1~5단계를 점으로 표시했다. 막대는 걸린 스텝 수다.
붉게 칠한 줄은 <b>정상 사이트에서는 해냈는데 결함 사이트에서 못 한 사람</b>이다.</p>
<div class="tablewrap"><table>
<thead><tr><th></th>{{axes}}{{head}}</tr></thead>
<tbody>{{rows}}</tbody>
</table></div>

<h2>축을 묶어서 — 낮음(1-2) vs 높음(4-5)</h2>
<p>값마다 인원이 적어 옆칸끼리는 비교할 수 없다. 양 끝만 묶어서 본다.</p>
<div class="tablewrap"><table>
<thead><tr><th></th>{{band_head}}</tr></thead>
<tbody>{{bands}}</tbody>
</table></div>

<h2>뒤집힌 사람들</h2>
<p>이 사람들이 결함의 대가를 치른다. 마지막 생각은 기록에서 그대로 옮겼다.</p>
<ul class="notes">{{notes}}</ul>

<footer>숫자는 <span class="mono">logs/</span> 의 기록에서 직접 읽어 만들었다.
다시 만들려면 <span class="mono">python report_html.py &lt;run_id&gt; &lt;run_id&gt;</span>.</footer>
</div>
"""


def main() -> int:
    ap = argparse.ArgumentParser(description="실행 결과를 한눈에 보는 HTML")
    ap.add_argument("runs", nargs="+")
    ap.add_argument("--out", default="결과.html")
    args = ap.parse_args()

    runs = [load(r) for r in args.runs]
    with open(os.path.join("personas", "personas.json"), encoding="utf-8") as f:
        goal = json.load(f).get("goal", "")
    doc = build(runs, goal)
    with open(args.out, "w", encoding="utf-8", newline="\n") as f:
        f.write(doc)
    print("저장: %s" % args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
