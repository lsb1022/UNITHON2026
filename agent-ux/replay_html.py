"""탐색 기록을 다시 재생하는 단일 HTML 을 만든다.

    python replay_html.py v2_buggy10 --out 재생.html
    python replay_html.py v2_clean10 v2_buggy10 --out 재생.html --limit 6

스크린샷을 다시 붙이는 것이 아니다. 스텝마다 저장해둔 **요소의 좌표·크기·
글자·대비·가려짐**으로 그 순간 화면을 다시 그린다. 그래서 재생 화면에는
사람 눈에 보이던 것만이 아니라 **왜 안 보였는지**까지 함께 나온다.

실제 쇼핑몰을 iframe 으로 띄워 조작을 재연하는 방법도 있지만, 페이지가 다른
주소에 있으면 교차 출처 정책에 막혀 내부를 건드릴 수 없다. 기록으로 다시
그리는 편이 어디서든 열리고, 우리가 무엇을 측정했는지도 같이 보여준다.

결과는 인터넷 연결이나 서버 없이 열리는 파일 하나다.
"""
from __future__ import annotations

import argparse
import json
import os
import sys

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:  # noqa: BLE001
        pass

END = {"goal_reached": ("달성", "ok"), "gave_up": ("포기", "bad"),
       "max_steps": ("스텝 소진", "warn"), "loop_detected": ("맴돌다 중단", "warn"),
       "budget_stop": ("예산 상한", "mute"), "error": ("오류", "bad")}

# 재생에 필요한 것만. 전체를 넣으면 파일이 몇 배로 커진다.
KEEP = ("id", "text", "page_x", "page_y", "w", "h", "below_fold", "occluded",
        "contrast", "font_size", "keyboard_reachable", "input_type", "value")


def pack(run_id: str, limit: int) -> list[dict]:
    d = os.path.join("logs", run_id)
    with open(os.path.join(d, "index.json"), encoding="utf-8") as f:
        idx = json.load(f)
    out = []
    for p in idx["personas"][:limit]:
        with open(os.path.join(d, p["file"]), encoding="utf-8") as f:
            t = json.load(f)
        steps = []
        for s in t["steps"]:
            snap = s["snapshot"]
            steps.append({
                "n": s["step"],
                "thought": s["thought"],
                "action": s["action"],
                "note": (s.get("outcome") or {}).get("note") or "",
                "target": s["action"].get("target"),
                "url": snap["url"].split("/")[-1],
                "fullUrl": snap["url"],
                "title": snap["title"],
                "fold": snap["fold_y"],
                "scroll": snap["scroll_y"],
                "height": snap["page_height"],
                "body": {"contrast": snap.get("body_contrast"),
                         "font": snap.get("body_font_size")},
                "els": [{k: e.get(k) for k in KEEP} for e in snap["elements"]],
            })
        out.append({
            "run": run_id,
            "variant": t["variant"],
            "id": t["persona"]["id"],
            "label": t["persona"].get("label", ""),
            "traits": t["persona"].get("traits", {}),
            "dwell": t["persona"].get("dwell_ms"),
            "maxSteps": t["persona"].get("max_steps"),
            "prompt": t["persona"].get("prompt", ""),
            "end": t["end_reason"],
            "endLabel": END.get(t["end_reason"], (t["end_reason"], "mute"))[0],
            "endCls": END.get(t["end_reason"], (t["end_reason"], "mute"))[1],
            "steps": steps,
        })
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="탐색 기록 재생 HTML")
    ap.add_argument("runs", nargs="+")
    ap.add_argument("--out", default="재생.html")
    ap.add_argument("--limit", type=int, default=10, help="실행당 최대 인원")
    ap.add_argument("--live", action="store_true",
                    help="실제 사이트를 iframe 으로 띄우고 그 위에 겹쳐 보여준다. "
                         "쇼핑몰과 같은 주소에서 열어야 동작한다")
    args = ap.parse_args()

    data = []
    for r in args.runs:
        data += pack(r, args.limit)
    with open(os.path.join("personas", "personas.json"), encoding="utf-8") as f:
        goal = json.load(f).get("goal", "")

    if args.live:
        # 실제 사이트 위에 겹치는 판. 쇼핑몰과 같은 주소에서 열어야 동작한다.
        from uxagent.live_template import LIVE_TEMPLATE
        tpl = LIVE_TEMPLATE
    else:
        tpl = TEMPLATE
    doc = tpl.replace("__DATA__", json.dumps(data, ensure_ascii=False))
    doc = doc.replace("__GOAL__", json.dumps(goal, ensure_ascii=False))
    with open(args.out, "w", encoding="utf-8", newline="\n") as f:
        f.write(doc)
    size = os.path.getsize(args.out) / 1024
    print("저장: %s  (%d명 / %.0fKB)" % (args.out, len(data), size))
    return 0


TEMPLATE = r"""<meta charset="utf-8">
<title>페르소나 재생</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&family=IBM+Plex+Sans+KR:wght@400;500;600;700&display=swap">
<style>
:root{
  --bg:#EFF2F5; --card:#FFF; --ink:#141A21; --soft:#4A5765; --mute:#7C8896;
  --line:#DCE1E7; --line2:#EEF1F4; --accent:#0F5C7A; --accent-bg:#E2EEF4;
  --ok:#1F7A5A; --ok-bg:#E4F2EC; --bad:#A63A2B; --bad-bg:#F8E7E3;
  --warn:#8A5A12; --warn-bg:#F7EEDD;
  --page:#FFFFFF; --box:#E7EBEF; --boxline:#C9D1D9;
  --f:"IBM Plex Sans KR",system-ui,"Malgun Gothic",sans-serif;
  --m:"IBM Plex Mono",ui-monospace,monospace;
}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){
  --bg:#0D1219; --card:#151B23; --ink:#E6EBF0; --soft:#AEB9C5; --mute:#7F8B98;
  --line:#28313B; --line2:#1D242C; --accent:#69B4D6; --accent-bg:#12303D;
  --ok:#6DBF9C; --ok-bg:#152A22; --bad:#DE8B7A; --bad-bg:#2E1E1A;
  --warn:#D6AC66; --warn-bg:#2B2416;
  --page:#1B222B; --box:#232C36; --boxline:#33404D;
}}
:root[data-theme="dark"]{
  --bg:#0D1219; --card:#151B23; --ink:#E6EBF0; --soft:#AEB9C5; --mute:#7F8B98;
  --line:#28313B; --line2:#1D242C; --accent:#69B4D6; --accent-bg:#12303D;
  --ok:#6DBF9C; --ok-bg:#152A22; --bad:#DE8B7A; --bad-bg:#2E1E1A;
  --warn:#D6AC66; --warn-bg:#2B2416;
  --page:#1B222B; --box:#232C36; --boxline:#33404D;
}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font-family:var(--f);line-height:1.55}
.top{padding:1rem clamp(1rem,3vw,2rem) .6rem;border-bottom:1px solid var(--line)}
h1{margin:0;font-size:1.15rem;font-weight:700}
.goal{font-family:var(--m);font-size:.82rem;color:var(--accent);background:var(--accent-bg);
  display:inline-block;padding:.2rem .55rem;border-radius:3px;margin-top:.4rem}
.layout{display:grid;grid-template-columns:15rem 1fr;gap:1px;background:var(--line);
  min-height:calc(100vh - 5rem)}
@media(max-width:820px){.layout{grid-template-columns:1fr}}
.side,.main{background:var(--bg)}
.side{padding:.7rem;overflow-y:auto;max-height:calc(100vh - 5rem)}
.pbtn{display:block;width:100%;text-align:left;background:var(--card);border:1px solid var(--line);
  border-radius:5px;padding:.5rem .6rem;margin-bottom:.4rem;cursor:pointer;font-family:var(--f);
  color:var(--ink);font-size:.82rem}
.pbtn:hover{border-color:var(--accent)}
.pbtn[aria-current="true"]{border-color:var(--accent);background:var(--accent-bg)}
.pbtn .row1{display:flex;justify-content:space-between;align-items:center;gap:.4rem}
.pbtn b{font-family:var(--m)}
.pbtn .lab{color:var(--mute);font-size:.74rem;font-family:var(--m)}
.pill{font-size:.7rem;padding:.08rem .42rem;border-radius:99px;white-space:nowrap}
.pill.ok{color:var(--ok);background:var(--ok-bg)}
.pill.bad{color:var(--bad);background:var(--bad-bg)}
.pill.warn{color:var(--warn);background:var(--warn-bg)}
.pill.mute{color:var(--mute);background:var(--line2)}
.main{padding:.8rem clamp(.7rem,2vw,1.4rem)}
.bar{display:flex;align-items:center;gap:.5rem;flex-wrap:wrap;margin-bottom:.6rem}
button.ctl{font-family:var(--m);font-size:.8rem;padding:.3rem .7rem;border-radius:4px;
  border:1px solid var(--line);background:var(--card);color:var(--ink);cursor:pointer}
button.ctl:hover{border-color:var(--accent)}
button.ctl:disabled{opacity:.4;cursor:default}
input[type=range]{flex:1;min-width:8rem;accent-color:var(--accent)}
.stepno{font-family:var(--m);font-size:.8rem;color:var(--mute);white-space:nowrap}
.thought{background:var(--card);border:1px solid var(--line);border-left:3px solid var(--accent);
  border-radius:5px;padding:.6rem .8rem;margin-bottom:.5rem;font-size:.9rem}
.act{font-family:var(--m);font-size:.8rem;color:var(--soft);margin-top:.35rem}
.act .k{color:var(--accent)}
.metrics{display:flex;gap:.4rem;flex-wrap:wrap;margin-bottom:.6rem}
.metrics span{font-family:var(--m);font-size:.74rem;padding:.15rem .5rem;border-radius:3px;
  background:var(--card);border:1px solid var(--line);color:var(--soft)}
.metrics span.hot{color:var(--bad);border-color:var(--bad);background:var(--bad-bg)}
.stage{background:var(--card);border:1px solid var(--line);border-radius:6px;padding:.6rem;
  overflow:auto;max-height:62vh}
.page{position:relative;background:var(--page);border:1px solid var(--boxline);
  transform-origin:top left}
.el{position:absolute;border:1px solid var(--boxline);background:var(--box);border-radius:2px;
  font-size:9px;line-height:1.1;padding:1px 2px;overflow:hidden;color:var(--soft);
  white-space:nowrap;text-overflow:ellipsis}
.el.low{border-color:var(--warn);color:var(--warn)}
.el.occ{border-color:var(--bad);background:var(--bad-bg);color:var(--bad)}
.el.kb{border-style:dashed}
.el.hit{outline:2px solid var(--accent);outline-offset:1px;background:var(--accent-bg);
  color:var(--accent);z-index:5;font-weight:600}
.fold{position:absolute;left:0;right:0;border-top:1px dashed var(--mute);opacity:.7}
.fold b{position:absolute;right:2px;top:-14px;font-family:var(--m);font-size:9px;color:var(--mute)}
.legend{margin-top:.5rem;font-family:var(--m);font-size:.72rem;color:var(--mute);
  display:flex;gap:.9rem;flex-wrap:wrap}
.legend i{display:inline-block;width:9px;height:9px;border:1px solid var(--boxline);
  margin-right:.25rem;vertical-align:-1px;border-radius:2px}
.legend i.low{border-color:var(--warn)} .legend i.occ{border-color:var(--bad);background:var(--bad-bg)}
.legend i.kb{border-style:dashed} .legend i.hit{outline:2px solid var(--accent);outline-offset:0}
</style>
<div class="top">
  <h1>페르소나 재생</h1>
  <div class="goal" id="goal"></div>
</div>
<div class="layout">
  <div class="side" id="side"></div>
  <div class="main">
    <div class="bar">
      <button class="ctl" id="prev">◀ 이전</button>
      <button class="ctl" id="play">▶ 재생</button>
      <button class="ctl" id="next">다음 ▶</button>
      <input type="range" id="range" min="0" value="0">
      <span class="stepno" id="stepno"></span>
    </div>
    <div class="thought" id="thought"></div>
    <div class="metrics" id="metrics"></div>
    <div class="stage"><div class="page" id="page"></div></div>
    <div class="legend">
      <span><i></i>보통</span>
      <span><i class="low"></i>대비 3:1 미만</span>
      <span><i class="occ"></i>가려짐</span>
      <span><i class="kb"></i>키보드로 못 감</span>
      <span><i class="hit"></i>이 스텝에서 지목한 요소</span>
      <span>점선 가로줄 = 접힘선(스크롤 없이 보이는 한계)</span>
    </div>
  </div>
</div>
<script id="data" type="application/json">__DATA__</script>
<script>
const DATA = JSON.parse(document.getElementById("data").textContent);
const GOAL = __GOAL__;
document.getElementById("goal").textContent = "목표 · " + GOAL;

let pi = 0, si = 0, timer = null;
const side = document.getElementById("side"), page = document.getElementById("page");
const $ = (id) => document.getElementById(id);

function renderSide(){
  side.innerHTML = "";
  DATA.forEach((p, i) => {
    const b = document.createElement("button");
    b.className = "pbtn";
    b.setAttribute("aria-current", i === pi ? "true" : "false");
    b.innerHTML = '<span class="row1"><b>' + p.id + '</b>'
      + '<span class="pill ' + p.endCls + '">' + p.endLabel + '</span></span>'
      + '<span class="lab">' + p.variant + ' · ' + p.label + ' · ' + p.steps.length + '스텝</span>';
    b.onclick = () => { pi = i; si = 0; stop(); render(); };
    side.appendChild(b);
  });
}

function render(){
  const p = DATA[pi], s = p.steps[si];
  renderSide();
  $("range").max = p.steps.length - 1;
  $("range").value = si;
  $("stepno").textContent = (si + 1) + " / " + p.steps.length + "  ·  " + s.url;
  $("prev").disabled = si === 0;
  $("next").disabled = si === p.steps.length - 1;

  const tgt = s.target ? (" <span class=\"k\">" + s.target + "</span>") : "";
  const val = s.action.value ? (' "' + s.action.value + '"') : "";
  $("thought").innerHTML = s.thought
    + '<div class="act">' + s.action.type + tgt + val
    + (s.note ? '  →  ' + s.note : '') + '</div>';

  const els = s.els;
  const occ = els.filter(e => e.occluded).length;
  const low = els.filter(e => (e.contrast ?? 99) < 3).length;
  const kb = els.filter(e => !e.keyboard_reachable).length;
  const m = [["요소 " + els.length, 0], ["가려짐 " + occ, occ > 0],
             ["저대비 " + low, low > 0], ["키보드불가 " + kb, kb > 0],
             ["본문 " + s.body.contrast + ":1", s.body.contrast < 4.5],
             ["본문 " + s.body.font + "px", s.body.font < 14]];
  $("metrics").innerHTML = m.map(([t, hot]) =>
    '<span class="' + (hot ? "hot" : "") + '">' + t + '</span>').join("");

  // 문서 전체를 담을 크기로 그리고, 가로폭에 맞춰 축소한다.
  const W = 1280, H = Math.max(s.height, 900);
  page.style.width = W + "px";
  page.style.height = H + "px";
  const avail = page.parentElement.clientWidth - 24;
  const scale = Math.min(1, avail / W);
  page.style.transform = "scale(" + scale + ")";
  page.parentElement.style.height = (H * scale + 20) + "px";

  let html = "";
  for (const e of els){
    const cls = ["el"];
    if ((e.contrast ?? 99) < 3) cls.push("low");
    if (e.occluded) cls.push("occ");
    if (!e.keyboard_reachable) cls.push("kb");
    if (e.id === s.target) cls.push("hit");
    const txt = (e.text || e.id).slice(0, 40);
    html += '<div class="' + cls.join(" ") + '" style="left:' + e.page_x + 'px;top:'
      + e.page_y + 'px;width:' + Math.max(e.w, 8) + 'px;height:' + Math.max(e.h, 8)
      + 'px" title="' + (e.text || "").replace(/"/g, "&quot;") + ' · '
      + (e.contrast ?? "?") + ':1 · ' + e.w + '×' + e.h + '">' + txt + '</div>';
  }
  html += '<div class="fold" style="top:' + (s.scroll + s.fold) + 'px"><b>접힘선</b></div>';
  page.innerHTML = html;
}

function step(d){ const p = DATA[pi]; si = Math.max(0, Math.min(p.steps.length - 1, si + d)); render(); }
function stop(){ if (timer){ clearInterval(timer); timer = null; $("play").textContent = "▶ 재생"; } }
$("prev").onclick = () => { stop(); step(-1); };
$("next").onclick = () => { stop(); step(1); };
$("range").oninput = (e) => { stop(); si = +e.target.value; render(); };
$("play").onclick = () => {
  if (timer) return stop();
  $("play").textContent = "❚❚ 멈춤";
  timer = setInterval(() => {
    if (si >= DATA[pi].steps.length - 1) return stop();
    si++; render();
  }, 1400);
};
addEventListener("keydown", (e) => {
  if (e.key === "ArrowLeft") { stop(); step(-1); }
  if (e.key === "ArrowRight") { stop(); step(1); }
});
addEventListener("resize", render);
render();
</script>
"""


if __name__ == "__main__":
    raise SystemExit(main())
