"""계산된 시각 정보 스냅샷.

스크린샷을 쓰지 않는다. 대신 브라우저가 이미 레이아웃 단계에서 계산해둔 값
— 좌표, 크기, 색 대비, 화면 접힘선, 가림 여부 — 을 뽑아 텍스트로 넘긴다.

UXCascade는 스크린샷을 주고도 시각적 인지에 실패했다. 픽셀을 다시 보게 하는
대신, 브라우저가 이미 알고 있는 숫자를 그대로 건네는 접근이다.

에이전트는 좌표가 아니라 이름(data-agent-id)으로 요소를 지목한다.
좌표로 클릭하면 화면이 조금만 바뀌어도 깨진다.
"""

# 페이지 안에서 실행되는 수집 스크립트.
# 반환값은 JSON 직렬화 가능한 dict 하나.
_COLLECT_JS = r"""
() => {
  const MAX_TEXT = 80;

  /* ── 색 계산 ─────────────────────────────────────────── */
  const nums = (s) => (s.match(/[\d.]+/g) || []).map(Number);
  const isTransparent = (s) => { const n = nums(s); return n.length >= 4 && n[3] < 0.1; };
  const lum = (rgb) => {
    const a = rgb.slice(0, 3).map((v) => {
      v /= 255;
      return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4);
    });
    return 0.2126 * a[0] + 0.7152 * a[1] + 0.0722 * a[2];
  };
  const ratio = (a, b) => {
    const L1 = lum(a), L2 = lum(b);
    return (Math.max(L1, L2) + 0.05) / (Math.min(L1, L2) + 0.05);
  };
  // 배경이 투명하면 조상으로 거슬러 올라가 실제로 깔린 색을 찾는다.
  const effectiveBg = (el) => {
    let n = el;
    while (n && n.nodeType === 1) {
      const bg = getComputedStyle(n).backgroundColor;
      if (bg && !isTransparent(bg)) { const v = nums(bg); if (v.length >= 3) return v; }
      n = n.parentElement;
    }
    return [255, 255, 255];
  };
  const contrastOf = (el) => {
    try {
      const fg = nums(getComputedStyle(el).color);
      if (fg.length < 3) return null;
      return Math.round(ratio(fg, effectiveBg(el)) * 10) / 10;
    } catch (e) { return null; }
  };

  /* ── 텍스트 추출 ─────────────────────────────────────── */
  const labelOf = (el) => {
    const cands = [
      el.getAttribute("aria-label"),
      (el.innerText || "").trim(),
      el.getAttribute("placeholder"),
      el.getAttribute("value"),
      el.getAttribute("title"),
      el.getAttribute("alt"),
      el.tagName === "SELECT" && el.selectedOptions[0]
        ? el.selectedOptions[0].textContent : null,
    ];
    for (const c of cands) {
      if (c && c.trim()) {
        const t = c.trim().replace(/\s+/g, " ");
        return t.length > MAX_TEXT ? t.slice(0, MAX_TEXT) + "…" : t;
      }
    }
    return "";
  };

  /* ── 조작 가능 요소 수집 ─────────────────────────────── */
  const NATIVE = "a[href],button,input,select,textarea,summary,[role=button]," +
                 "[role=link],[role=checkbox],[role=tab],[contenteditable=true]";

  const seen = new Set();
  const pool = [];
  document.querySelectorAll(NATIVE).forEach((el) => { seen.add(el); pool.push(el); });

  // cursor:pointer 휴리스틱 — flawed 사이트의 <div class="fake-btn"> 같은
  // '가짜 버튼'을 잡는다. 마우스 쓰는 사람 눈에는 버튼으로 보이기 때문에
  // 에이전트에게도 보여야 한다. 대신 keyboard_reachable=false로 표시해
  // 나중에 접근성 결함으로 집계할 수 있게 한다.
  document.querySelectorAll("div,span,li,td,label,i,p").forEach((el) => {
    if (seen.has(el)) return;
    if (getComputedStyle(el).cursor !== "pointer") return;
    if (el.querySelector(NATIVE)) return;          // 자식이 진짜 버튼이면 건너뜀
    // <label><input type=radio><span>화이트</span></label> 처럼 진짜 컨트롤을
    // 감싼 label 안의 장식용 자식은 건너뛴다. label은 NATIVE 목록에 없어서
    // seen에 들어가지 않으므로 아래 nested 검사만으로는 걸러지지 않는다.
    // 이걸 놓치면 접근성이 올바른 clean 사이트의 상품 옵션이 매번
    // '키보드 도달 불가 가짜 버튼' 7건으로 잡혀 오탐률이 오염된다.
    const lab = el.closest("label");
    if (lab && lab.querySelector(NATIVE)) return;
    let p = el.parentElement, nested = false;
    while (p) { if (seen.has(p)) { nested = true; break; } p = p.parentElement; }
    if (nested) return;
    seen.add(el); pool.push(el);
  });

  const vw = window.innerWidth, vh = window.innerHeight;
  const counters = {};
  const elements = [];

  for (const el of pool) {
    const cs = getComputedStyle(el);
    if (cs.display === "none" || cs.visibility === "hidden") continue;
    if (parseFloat(cs.opacity) === 0) continue;
    const r = el.getBoundingClientRect();
    if (r.width < 1 || r.height < 1) continue;
    // 뷰포트 위/좌로 완전히 벗어난 것만 제외. 아래쪽은 below_fold로 표시해 남긴다.
    if (r.bottom < 0 || r.right < 0) continue;

    const tag = el.tagName.toLowerCase();
    const key = tag === "a" ? "link" : tag;
    counters[key] = (counters[key] || 0) + 1;
    const aid = `${key}_${counters[key]}`;
    el.setAttribute("data-agent-id", aid);

    // 가림 판정: 요소 중심점에서 히트 테스트
    let occluded = false;
    const cx = Math.min(Math.max(r.left + r.width / 2, 1), vw - 1);
    const cy = Math.min(Math.max(r.top + r.height / 2, 1), vh - 1);
    if (r.top < vh && r.bottom > 0) {
      const hit = document.elementFromPoint(cx, cy);
      occluded = !hit || !(hit === el || el.contains(hit) || hit.contains(el));
    }

    const disabled = el.disabled === true || el.getAttribute("aria-disabled") === "true";
    const faded = parseFloat(cs.opacity) < 0.5 || cs.filter.includes("grayscale");
    const ti = el.getAttribute("tabindex");
    const nativelyFocusable = /^(a|button|input|select|textarea|summary)$/.test(tag);
    const fontSize = Math.round(parseFloat(cs.fontSize) * 10) / 10;

    elements.push({
      id: aid,
      tag: tag,
      role: el.getAttribute("role") || null,
      text: labelOf(el),
      // x,y 는 뷰포트 기준 (마찰 판정용). page_x,page_y 는 문서 기준으로,
      // 스크롤 위치와 무관하게 전체 페이지 와이어프레임을 그릴 때 쓴다.
      // 이게 없으면 스크롤을 내린 스텝의 좌표가 문서상 어디였는지 복원 못 한다.
      x: Math.round(r.left), y: Math.round(r.top),
      page_x: Math.round(r.left + window.scrollX),
      page_y: Math.round(r.top + window.scrollY),
      w: Math.round(r.width), h: Math.round(r.height),
      below_fold: r.top >= vh,
      occluded: occluded,
      contrast: contrastOf(el),
      font_size: fontSize,
      disabled_look: disabled || faded,
      // WCAG 1.4.3은 '비활성 UI 컴포넌트'를 대비 기준에서 면제한다.
      // disabled 속성이 실제로 붙은 것만 면제하고, opacity/grayscale로
      // '비활성처럼 보이기만' 하는 것(flawed의 결함)은 면제하지 않는다.
      disabled_attr: disabled,
      // 마우스로는 눌리는데 키보드로는 도달 못 하는 요소를 구분한다.
      keyboard_reachable: nativelyFocusable ? ti !== "-1" : ti !== null && ti !== "-1",
      href: tag === "a" ? (el.getAttribute("href") || null) : null,
      input_type: tag === "input" ? (el.getAttribute("type") || "text") : null,
      checked: (el.type === "checkbox" || el.type === "radio") ? !!el.checked : null,
      value: (tag === "input" || tag === "textarea") ? (el.value || "") : null,
    });
  }

  /* ── 페이지 수준 지표 ────────────────────────────────── */
  const de = document.documentElement;
  const imgs = [...document.images];
  const bodyCS = getComputedStyle(document.body);

  return {
    url: location.href,
    title: document.title,
    lang: de.lang || null,
    viewport: { w: vw, h: vh },
    fold_y: vh,                                   // 화면 접힘선 위치
    page_height: de.scrollHeight,
    scroll_y: Math.round(window.scrollY),
    horizontal_scroll: de.scrollWidth > de.clientWidth + 1,
    body_font_size: Math.round(parseFloat(bodyCS.fontSize) * 10) / 10,
    body_contrast: (() => {
      const fg = nums(bodyCS.color);
      return fg.length >= 3
        ? Math.round(ratio(fg, effectiveBg(document.body)) * 10) / 10 : null;
    })(),
    landmarks: {
      main: document.querySelectorAll("main").length,
      nav: document.querySelectorAll("nav").length,
      h1: document.querySelectorAll("h1").length,
    },
    images: { total: imgs.length, missing_alt: imgs.filter((i) => !i.hasAttribute("alt")).length },
    // 텍스트 본문 일부 — 에이전트가 페이지 성격을 파악하는 데 쓴다
    visible_text: (document.body.innerText || "").trim().replace(/\s+/g, " ").slice(0, 600),
    elements: elements,
  };
}
"""


async def take_snapshot(page):
    """페이지에서 계산된 시각 정보를 뽑는다."""
    return await page.evaluate(_COLLECT_JS)


# ── 프롬프트용 직렬화 ─────────────────────────────────────────────

def _flag_str(el: dict) -> str:
    """이 요소에서 사람이 겪을 마찰을 짧은 플래그로 압축한다."""
    f = []
    if el["below_fold"]:
        f.append("접힘선아래")
    if el["occluded"]:
        f.append("가려짐")
    if el["disabled_look"]:
        f.append("비활성처럼보임")
    c = el.get("contrast")
    if c is not None and c < 3.0 and not el.get("disabled_attr"):
        f.append(f"대비{c}:1")
    if el["w"] * el["h"] > 0 and (el["w"] < 24 or el["h"] < 24):
        f.append(f"작음{el['w']}x{el['h']}")
    fs = el.get("font_size")
    if fs and fs < 12:
        f.append(f"{fs}px")
    if not el["keyboard_reachable"]:
        f.append("키보드불가")
    return " ".join(f)


NEWLINE = chr(10)


def _shape(el: dict) -> tuple:
    """'같은 모양'의 열쇠 — **같은 세로줄에 같은 높이로 반복되는 것**.

    너비는 넣지 않는다. 글자 길이에 따라 제각각이라 넣으면 아무것도 안 묶인다.
    왼쪽 끝과 높이가 같으면 한 줄로 늘어선 목록(사이드바 차례, 메뉴)이다.
    격자로 놓인 상품 카드는 칸마다 왼쪽 끝이 달라 묶이지 않는다 — 상품은
    하나하나가 다른 선택지라 접으면 안 된다.
    """
    return (el["tag"], el.get("role"), el.get("input_type"),
            round(el["h"] / 4), round(el["x"] / 20))


def _band(el: dict, fold: int) -> int:
    """지금 사람 눈에 어디쯤 있나. 0=화면 안, 1=접힘선 아래, 2=스크롤로 지나간 위쪽."""
    if el["y"] < 0:
        return 2
    return 0 if el["y"] < fold else 1


def pick_for_prompt(snap: dict, limit: int) -> tuple[list[dict], dict]:
    """이 화면에서 사람이 실제로 볼 만한 요소를 고른다.

    예전에는 문서 위에서부터 N개를 잘랐다. 우리 테스트베드는 요소가 20~30개라
    그래도 전부 들어갔지만, 남의 사이트는 사정이 다르다 — 한국어 위키백과
    한 페이지에 조작 가능한 요소가 **3,079개** 있었다. 위에서부터 25개를 자르면
    상단 메뉴만 보고 본문은 영영 못 본다.

    그래서 사람이 보는 순서대로 고른다:

    1. **지금 화면 안**을 위에서 아래로 — 사람도 스크롤한 만큼만 본다
    2. 자리가 남으면 접힘선 **바로 아래**를 조금 (곧 보일 것)
    3. 그래도 남으면 스크롤로 **지나간 위쪽**

    자리가 모자라면 **반복되는 것을 접는다.** 같은 크기·같은 태그가 줄줄이
    있으면(상품 카드, 목록 항목) 앞의 몇 개만 남기고 "같은 것 N개 더"로 적는다.
    사람도 목록을 한 줄씩 다 읽지 않는다.

    **요소가 상한 안에 들어오면 아무것도 접지 않는다.** 우리 테스트베드는
    예전과 똑같이 동작한다 — 앞서 쌓은 기록과 비교가 깨지지 않아야 한다.
    """
    els = snap["elements"]
    fold = snap.get("fold_y") or snap["viewport"]["h"]
    note = {"total": len(els), "hidden_below": 0, "folded": 0, "nameless": 0}

    if len(els) <= limit:
        return sorted(els, key=lambda e: (e["below_fold"], e["y"], e["x"])), note

    # 접기와 걸러내기는 **페이지가 상한보다 한참 클 때만** 한다. 우리 테스트베드는
    # 한 화면에 20~40개라 조금 넘칠 뿐인데 여기서 접으면 상품 카드가 사라져
    # 셔츠를 못 찾게 된다. 위키백과처럼 수천 개인 곳에서만 걸려야 한다.
    huge = len(els) > limit * 3

    usable = list(els)
    if huge:
        # 이름도 입력칸도 링크도 아닌 것은 사람이 무엇인지 알 수 없다 —
        # 눌러도 무엇을 누른 건지 말할 수 없으므로 자리를 내준다.
        named = [e for e in els
                 if (e["text"] or "").strip() or e.get("input_type") or e.get("href")]
        if named:
            note["nameless"] = len(els) - len(named)
            usable = named

    ordered = sorted(usable, key=lambda e: (_band(e, fold), e["y"], e["x"]))

    out: list[dict] = []
    shapes: dict[tuple, int] = {}
    # 한 모양에서 몇 개까지 보여줄지. 목록이 있다는 것만 알면 되고
    # 그 안에서 무엇을 고를지는 글자로 판단한다.
    per_shape = 6 if huge else limit
    for el in ordered:
        if len(out) >= limit:
            break
        key = _shape(el)
        seen = shapes.get(key, 0)
        if seen >= per_shape:
            note["folded"] += 1
            continue
        shapes[key] = seen + 1
        out.append(el)

    shown = {id(e) for e in out}
    note["hidden_below"] = sum(1 for e in ordered
                               if id(e) not in shown and _band(e, fold) == 1)
    return out, note


def render_for_prompt(snap: dict, limit: int = 45) -> str:
    """스냅샷을 LLM이 읽을 텍스트로 바꾼다.

    좌표를 그대로 나열하지 않고, 사람이 겪을 마찰만 플래그로 남긴다.
    토큰을 아끼면서 '무엇이 눈에 띄고 무엇이 안 띄는지'는 보존한다.
    """
    lines = [
        f"URL: {snap['url']}",
        f"제목: {snap['title'] or '(없음)'}",
    ]
    warn = []
    if snap["horizontal_scroll"]:
        warn.append("가로 스크롤 발생")
    if snap["body_contrast"] is not None and snap["body_contrast"] < 4.5:
        warn.append(f"본문 대비 {snap['body_contrast']}:1")
    if snap["body_font_size"] < 14:
        warn.append(f"본문 {snap['body_font_size']}px")
    if warn:
        lines.append("화면 상태: " + ", ".join(warn))

    lines.append(f"본문 일부: {snap['visible_text'][:300]}")
    lines.append("")

    els, note = pick_for_prompt(snap, limit)
    fold = snap.get("fold_y") or snap["viewport"]["h"]
    in_view = sum(1 for e in els if _band(e, fold) == 0)

    if note["total"] <= limit:
        lines.append(f"조작 가능한 요소 ({note['total']}개, 상위 {limit}개 표시):")
    else:
        # 무엇이 빠졌는지 말해줘야 "여기 없네" 하고 포기하지 않고 스크롤한다.
        lines.append(
            "조작 가능한 요소 (이 페이지 전체 %d개 중 지금 화면 위주로 %d개 표시"
            "%s):" % (note["total"], len(els),
                      ", 화면 안 %d개" % in_view if in_view else ""))

    for el in els:
        text = el["text"] or "(텍스트 없음)"
        flags = _flag_str(el)
        where = ""
        band = _band(el, fold)
        if band == 1:
            where = " ⟨접힘선 아래⟩"
        elif band == 2:
            where = " ⟨스크롤로 지나감⟩"
        extra = ""
        if el["input_type"]:
            extra = f" [{el['input_type']}]"
            if el["value"]:
                extra += f" 입력값=\"{el['value'][:20]}\""
        if el["checked"] is not None:
            extra += " [체크됨]" if el["checked"] else " [체크안됨]"
        lines.append(
            f"  {el['id']}: \"{text}\"{extra}" + (f"  ⟨{flags}⟩" if flags else "") + where
        )

    rest = note["total"] - len(els)
    if rest > 0:
        tail = ["  … 외 %d개" % rest]
        if note["folded"]:
            tail.append("(같은 모양이 반복되는 것 %d개 접음)" % note["folded"])
        if note["hidden_below"]:
            tail.append("아래로 스크롤하면 %d개 더 있습니다" % note["hidden_below"])
        if note["nameless"]:
            tail.append("이름 없는 요소 %d개 제외" % note["nameless"])
        lines.append(" ".join(tail))
    return NEWLINE.join(lines)
