"""실제 화면 위에 겹쳐 보여주는 재생 페이지 템플릿.

기록으로 화면을 다시 그리는 대신, **진짜 사이트를 iframe 으로 띄우고 그 위에
표시를 얹는다.** 페르소나가 누른 자리에 테두리를 치고, 가려진 요소·저대비
요소를 덧칠하고, 접힘선을 긋는다.

교차 출처 정책 때문에 **쇼핑몰과 같은 주소에서 열어야** 화면 안을 스크롤할 수
있다. 그래서 이 파일은 저장소 루트(ux-testbed 와 나란히)에 두고
http://localhost:8000/replay-live.html 이나 GitHub Pages 주소로 연다.
다른 주소에서 열면 경고를 띄우고 겹치기만 한다.
"""

LIVE_TEMPLATE = r"""<!doctype html>
<html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>페르소나 재생 — 실제 화면 위에</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&family=IBM+Plex+Sans+KR:wght@400;500;600;700&display=swap">
<style>
:root{
  --bg:#EFF2F5; --card:#FFF; --ink:#141A21; --soft:#4A5765; --mute:#7C8896;
  --line:#DCE1E7; --line2:#EEF1F4; --accent:#0F5C7A; --accent-bg:#E2EEF4;
  --ok:#1F7A5A; --ok-bg:#E4F2EC; --bad:#A63A2B; --bad-bg:#F8E7E3;
  --warn:#8A5A12; --warn-bg:#F7EEDD;
  --f:"IBM Plex Sans KR",system-ui,"Malgun Gothic",sans-serif;
  --m:"IBM Plex Mono",ui-monospace,monospace;
}
@media (prefers-color-scheme:dark){:root{
  --bg:#0D1219; --card:#151B23; --ink:#E6EBF0; --soft:#AEB9C5; --mute:#7F8B98;
  --line:#28313B; --line2:#1D242C; --accent:#69B4D6; --accent-bg:#12303D;
  --ok:#6DBF9C; --ok-bg:#152A22; --bad:#DE8B7A; --bad-bg:#2E1E1A;
  --warn:#D6AC66; --warn-bg:#2B2416;
}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font-family:var(--f);line-height:1.55}
.top{padding:.8rem 1.2rem .5rem;border-bottom:1px solid var(--line);display:flex;
  align-items:baseline;gap:1rem;flex-wrap:wrap}
h1{margin:0;font-size:1.05rem;font-weight:700}
.goal{font-family:var(--m);font-size:.8rem;color:var(--accent);background:var(--accent-bg);
  padding:.15rem .5rem;border-radius:3px}
.warn{display:none;margin:.6rem 1.2rem;padding:.6rem .8rem;border-radius:5px;
  background:var(--warn-bg);color:var(--warn);font-size:.85rem;border:1px solid var(--warn)}
.layout{display:grid;grid-template-columns:14rem 1fr;gap:1px;background:var(--line)}
@media(max-width:900px){.layout{grid-template-columns:1fr}}
.side,.main{background:var(--bg)}
.side{padding:.6rem;overflow-y:auto;max-height:calc(100vh - 4rem)}
.pbtn{display:block;width:100%;text-align:left;background:var(--card);border:1px solid var(--line);
  border-radius:5px;padding:.45rem .55rem;margin-bottom:.35rem;cursor:pointer;
  font-family:var(--f);color:var(--ink);font-size:.8rem}
.pbtn[aria-current="true"]{border-color:var(--accent);background:var(--accent-bg)}
.pbtn .row1{display:flex;justify-content:space-between;gap:.4rem}
.pbtn b{font-family:var(--m)}
.pbtn .lab{color:var(--mute);font-size:.72rem;font-family:var(--m)}
.pill{font-size:.7rem;padding:.05rem .4rem;border-radius:99px;white-space:nowrap}
.pill.ok{color:var(--ok);background:var(--ok-bg)}
.pill.bad{color:var(--bad);background:var(--bad-bg)}
.pill.warn{color:var(--warn);background:var(--warn-bg)}
.pill.mute{color:var(--mute);background:var(--line2)}
.main{padding:.7rem 1rem 1.4rem}
.bar{display:flex;align-items:center;gap:.5rem;flex-wrap:wrap;margin-bottom:.5rem}
button.ctl{font-family:var(--m);font-size:.8rem;padding:.28rem .65rem;border-radius:4px;
  border:1px solid var(--line);background:var(--card);color:var(--ink);cursor:pointer}
button.ctl:disabled{opacity:.4;cursor:default}
input[type=range]{flex:1;min-width:7rem;accent-color:var(--accent)}
.stepno{font-family:var(--m);font-size:.78rem;color:var(--mute)}
.thought{background:var(--card);border:1px solid var(--line);border-left:3px solid var(--accent);
  border-radius:5px;padding:.55rem .75rem;margin-bottom:.45rem;font-size:.88rem}
.act{font-family:var(--m);font-size:.78rem;color:var(--soft);margin-top:.3rem}
.act .k{color:var(--accent)}
.metrics{display:flex;gap:.35rem;flex-wrap:wrap;margin-bottom:.55rem}
.metrics span{font-family:var(--m);font-size:.73rem;padding:.12rem .45rem;border-radius:3px;
  background:var(--card);border:1px solid var(--line);color:var(--soft)}
.metrics span.hot{color:var(--bad);border-color:var(--bad);background:var(--bad-bg)}
.stage{position:relative;width:100%;overflow:hidden;border:1px solid var(--line);
  border-radius:6px;background:#fff}
.inner{position:relative;width:1280px;height:800px;transform-origin:top left}
/* 기본은 마우스를 받지 않는다. 재생은 '그 사람이 본 화면'을 보여주는 것이라,
   보는 사람이 제멋대로 스크롤하면 접힘선과 겹친 표시가 어긋난다. */
iframe{width:1280px;height:800px;border:0;display:block;background:#fff;pointer-events:none}
iframe.free{pointer-events:auto}
.ovl{position:absolute;inset:0;pointer-events:none}
.mark{position:absolute;border:2px solid var(--accent);border-radius:3px;
  box-shadow:0 0 0 9999px rgba(0,0,0,.30);transition:all .35s ease}
.mark b{position:absolute;left:0;top:-1.5rem;background:var(--accent);color:#fff;
  font-family:var(--m);font-size:.72rem;padding:.1rem .4rem;border-radius:3px;white-space:nowrap}
.mark.ghost{border-style:dashed;border-color:var(--warn);box-shadow:0 0 0 9999px rgba(0,0,0,.30)}
.mark.ghost b{background:var(--warn)}
.cover{position:absolute;left:0;right:0;bottom:0;padding:.45rem .7rem;
  background:rgba(166,58,43,.92);color:#fff}
.cover b{font-family:var(--m);font-size:.74rem;font-weight:400}
.flag{position:absolute;border:1.5px solid var(--bad);border-radius:2px;
  background:rgba(166,58,43,.16)}
.flag.low{border-color:var(--warn);background:rgba(138,90,18,.13)}
.flag.kb{border-style:dashed;border-color:var(--warn);background:none}
.foldline{position:absolute;left:0;right:0;border-top:2px dashed rgba(120,130,140,.85)}
.foldline b{position:absolute;right:4px;top:-1.3rem;font-family:var(--m);font-size:.7rem;
  color:var(--mute);background:var(--card);padding:0 .3rem;border-radius:3px}
.legend{margin-top:.5rem;font-family:var(--m);font-size:.72rem;color:var(--mute);
  display:flex;gap:.9rem;flex-wrap:wrap}
.legend i{display:inline-block;width:10px;height:10px;margin-right:.25rem;vertical-align:-1px;
  border-radius:2px;border:2px solid var(--accent)}
.legend i.f{border-color:var(--bad);background:rgba(166,58,43,.16)}
.legend i.l{border-color:var(--warn);background:rgba(138,90,18,.13)}
.legend i.k{border-color:var(--warn);border-style:dashed;background:none}
label.tog{font-size:.78rem;color:var(--soft);display:flex;align-items:center;gap:.3rem}
</style></head><body data-base="">
<div class="top">
  <h1>페르소나 재생 — 실제 화면 위에</h1>
  <span class="goal" id="goal"></span>
</div>
<div class="warn" id="warn"></div>
<div class="layout">
  <div class="side" id="side"></div>
  <div class="main">
    <div class="bar">
      <button class="ctl" id="prev">&#9664;</button>
      <button class="ctl" id="play">&#9654; 재생</button>
      <button class="ctl" id="next">&#9654;</button>
      <input type="range" id="range" min="0" value="0">
      <span class="stepno" id="stepno"></span>
      <label class="tog"><input type="checkbox" id="showflags" checked> 결함 표시</label>
      <label class="tog"><input type="checkbox" id="freescroll"> 직접 스크롤</label>
    </div>
    <div class="thought" id="thought"></div>
    <div class="metrics" id="metrics"></div>
    <div class="stage" id="stage">
      <div class="inner" id="inner">
        <iframe id="frame" title="검사 대상 화면"></iframe>
        <div class="ovl" id="ovl"></div>
      </div>
    </div>
    <div class="legend">
      <span><i></i>이 스텝에서 누른 곳</span>
      <span><i class="f"></i>가려진 요소</span>
      <span><i class="l"></i>대비 3:1 미만</span>
      <span><i class="k"></i>키보드로 못 감</span>
      <span>점선 = 접힘선</span>
      <span>화면 안은 기본적으로 잠겨 있습니다 — 그때 보이던 그대로입니다</span>
    </div>
  </div>
</div>
<script id="data" type="application/json">__DATA__</script>
<script>
var DATA = JSON.parse(document.getElementById("data").textContent);
var GOAL = __GOAL__;
function $(id){ return document.getElementById(id); }
$("goal").textContent = "목표 · " + GOAL;

// 기록된 주소는 만들 때 쓰던 서버(localhost)일 수 있다. 지금 이 페이지가 놓인
// 자리를 기준으로 다시 맞춘다 — 그래야 배포한 주소에서도 같은 파일이 돈다.
var BASE = document.body.dataset.base
  || (location.pathname.replace(/[^/]*$/, "") + "ux-testbed");
function toLocal(u){
  var i = u.indexOf("/ux-testbed/");
  return i === -1 ? u : BASE + u.slice(i + "/ux-testbed".length);
}

var pi = 0, si = 0, timer = null, lastSrc = "";

function renderSide(){
  var side = $("side");
  side.innerHTML = "";
  DATA.forEach(function(p, i){
    var b = document.createElement("button");
    b.className = "pbtn";
    b.setAttribute("aria-current", i === pi ? "true" : "false");
    b.innerHTML = '<span class="row1"><b>' + p.id + '</b><span class="pill ' + p.endCls
      + '">' + p.endLabel + '</span></span><span class="lab">' + p.variant + ' · '
      + p.label + ' · ' + p.steps.length + '스텝</span>';
    b.onclick = function(){ pi = i; si = 0; stop(); render(true); };
    side.appendChild(b);
  });
}

function fit(){
  var w = $("stage").clientWidth;
  var s = Math.min(1, w / 1280);
  $("inner").style.transform = "scale(" + s + ")";
  $("stage").style.height = (800 * s) + "px";
}

function curScroll(st){
  // 직접 스크롤 중이면 지금 위치를, 아니면 기록된 위치를 기준으로 그린다.
  if ($("freescroll").checked){
    try { return $("frame").contentWindow.scrollY; } catch (e) { return st.scroll; }
  }
  return st.scroll;
}

function paint(){
  var st = DATA[pi].steps[si];
  var sc = curScroll(st);
  var html = "";
  if ($("showflags").checked){
    st.els.forEach(function(e){
      var y = e.page_y - sc;
      if (y > 800 || y + e.h < 0) return;
      var cls = "";
      if (e.occluded) cls = "flag";
      else if ((e.contrast === null || e.contrast === undefined ? 99 : e.contrast) < 3) cls = "flag low";
      else if (!e.keyboard_reachable) cls = "flag kb";
      if (!cls) return;
      html += '<div class="' + cls + '" style="left:' + e.page_x + 'px;top:' + y
        + 'px;width:' + Math.max(e.w, 6) + 'px;height:' + Math.max(e.h, 6) + 'px"></div>';
    });
  }
  html += '<div class="foldline" style="top:' + st.fold + 'px"><b>접힘선</b></div>';
  var hit = null;
  st.els.forEach(function(e){ if (e.id === st.target) hit = e; });
  if (hit){
    var hy = hit.page_y - sc;
    // 지금 화면의 같은 자리에 그때와 같은 것이 있는지 물어본다.
    // 팝업 안에만 있던 요소(닫기 버튼 등)는 지금 화면에 없어서 허공을 가리킨다.
    // 그 사실을 숨기지 않고 표시에 적는다.
    var ghost = false;
    try {
      var doc = $("frame").contentDocument;
      var at = doc.elementFromPoint(hit.page_x + hit.w / 2, hy + hit.h / 2);
      var now = at ? (at.innerText || at.value || "").trim().replace(/\s+/g, " ") : "";
      var then = String(hit.text || "").trim().replace(/\s+/g, " ");
      // 빈 자리에 떨어져도 '그때만 있던 요소'다. now 가 비어 있다고 통과시키면
      // 팝업 닫기 버튼 같은 것이 허공을 가리킨 채 아무 설명 없이 남는다.
      var head = then.slice(0, 8);
      var same = then && now && (now.indexOf(head) >= 0 || then.indexOf(now.slice(0, 8)) >= 0);
      if (!at || (then && !same)) ghost = true;
    } catch (err) { /* 다른 출처면 확인할 수 없다. 그냥 표시한다 */ }

    html += '<div class="mark' + (ghost ? " ghost" : "") + '" style="left:'
      + (hit.page_x - 3) + 'px;top:' + (hy - 3) + 'px;width:' + (hit.w + 6)
      + 'px;height:' + (hit.h + 6) + 'px"><b>' + st.action.type + ' · '
      + String(hit.text || st.target).slice(0, 24)
      + (ghost ? " — 지금 화면에는 없는 요소" : "") + '</b></div>';
  }

  // 그 순간 무엇이 화면을 덮고 있었는지 알린다. 지금 iframe 에는 없다.
  var occN = 0;
  st.els.forEach(function(e){ if (e.occluded) occN++; });
  if (occN > 0){
    html += '<div class="cover"><b>이 순간 화면을 덮고 있던 것이 있었습니다 — '
      + '가려진 요소 ' + occN + '개. 지금 띄운 화면에는 아직 안 떠 있습니다 '
      + '(자동 팝업은 로드 10초 후).</b></div>';
  }
  $("ovl").innerHTML = html;
}

function render(force){
  var p = DATA[pi], st = p.steps[si];
  renderSide();
  fit();
  $("range").max = p.steps.length - 1;
  $("range").value = si;
  $("stepno").textContent = (si + 1) + " / " + p.steps.length + " · " + st.url;
  $("prev").disabled = si === 0;
  $("next").disabled = si === p.steps.length - 1;

  var tgt = st.target ? ' <span class="k">' + st.target + '</span>' : "";
  var val = st.action.value ? ' "' + st.action.value + '"' : "";
  $("thought").innerHTML = st.thought + '<div class="act">' + st.action.type + tgt + val
    + (st.note ? "  →  " + st.note : "") + '</div>';

  var occ = 0, low = 0, kb = 0;
  st.els.forEach(function(e){
    if (e.occluded) occ++;
    if ((e.contrast === null || e.contrast === undefined ? 99 : e.contrast) < 3) low++;
    if (!e.keyboard_reachable) kb++;
  });
  var m = [["요소 " + st.els.length, false], ["가려짐 " + occ, occ > 0],
           ["저대비 " + low, low > 0], ["키보드불가 " + kb, kb > 0],
           ["본문 " + st.body.contrast + ":1", st.body.contrast < 4.5],
           ["본문 " + st.body.font + "px", st.body.font < 14]];
  $("metrics").innerHTML = m.map(function(x){
    return '<span class="' + (x[1] ? "hot" : "") + '">' + x[0] + '</span>';
  }).join("");

  var src = toLocal(st.fullUrl);
  var f = $("frame");
  if (force || src !== lastSrc){
    lastSrc = src;
    f.onload = function(){
      try {
        f.contentWindow.scrollTo(0, st.scroll);
        if ($("freescroll").checked){
          f.contentWindow.addEventListener("scroll", paint, {passive: true});
        }
        $("warn").style.display = "none";
      } catch (err) {
        $("warn").style.display = "block";
        $("warn").textContent = "이 페이지가 쇼핑몰과 다른 주소에 있어 화면 안을 "
          + "스크롤할 수 없습니다. 쇼핑몰과 같은 서버에 두고 여세요 "
          + "(예: http://localhost:8000/replay-live.html).";
      }
      paint();
    };
    f.src = src;
  } else {
    try { f.contentWindow.scrollTo(0, st.scroll); } catch (err) {}
    paint();
  }
}

function step(d){
  var p = DATA[pi];
  si = Math.max(0, Math.min(p.steps.length - 1, si + d));
  render();
}
function stop(){
  if (timer){ clearInterval(timer); timer = null; $("play").textContent = "▶ 재생"; }
}
$("prev").onclick = function(){ stop(); step(-1); };
$("next").onclick = function(){ stop(); step(1); };
$("range").oninput = function(e){ stop(); si = +e.target.value; render(); };
$("showflags").onchange = paint;
$("freescroll").onchange = function(){
  var f = $("frame");
  f.classList.toggle("free", this.checked);
  if (this.checked){
    // 화면 안을 직접 굴릴 수 있게 하되, 표시가 같이 따라가도록 붙잡아 둔다.
    try { f.contentWindow.addEventListener("scroll", paint, {passive: true}); }
    catch (e) {}
  } else {
    try {
      f.contentWindow.removeEventListener("scroll", paint);
      f.contentWindow.scrollTo(0, DATA[pi].steps[si].scroll);   // 기록 위치로 되돌린다
    } catch (e) {}
  }
  paint();
};
$("play").onclick = function(){
  if (timer) return stop();
  $("play").textContent = "❚❚ 멈춤";
  timer = setInterval(function(){
    if (si >= DATA[pi].steps.length - 1) return stop();
    si++; render();
  }, 1800);
};
addEventListener("keydown", function(e){
  if (e.key === "ArrowLeft"){ stop(); step(-1); }
  if (e.key === "ArrowRight"){ stop(); step(1); }
});
addEventListener("resize", function(){ fit(); paint(); });
render(true);
</script></body></html>
"""
