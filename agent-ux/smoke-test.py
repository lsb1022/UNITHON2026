"""답사기 스모크 테스트.

    python smoke-test.py

LLM 없이 돈다 (--mock 경로). 서버만 떠 있으면 된다:
    cd C:\\Users\\kamdo\\AI_Testing && python -m http.server 8000

여기서 검사하는 것은 '답사기가 죽지 않는다'가 아니라 **측정 기준선이
흔들리지 않는다**이다. clean 에서 시각 결함이 하나라도 세어지면 오탐률
(차별점 ①)이 오염되므로, 그게 곧 실패다.
"""
from __future__ import annotations

import asyncio
import sys

sys.stdout.reconfigure(encoding="utf-8")

from uxagent import config, discover
from uxagent import explore as E
from uxagent import scout as SC
from uxagent import goals as G
from uxagent import persona as PS
from uxagent import survey as S
from uxagent.snapshot import take_snapshot

PASS, FAIL = [], []


def check(name: str, ok: bool, detail: str = "") -> None:
    (PASS if ok else FAIL).append(name)
    mark = "  OK  " if ok else " FAIL "
    print("[%s] %s%s" % (mark, name, ("  — " + detail) if detail else ""))


# ── 1. 판단 표현 필터 (브라우저 불필요) ────────────────────────────

def test_filter() -> None:
    print("\n── 판단 표현 필터 ──")
    cases = [
        ("수량 비교는 통과", "상품 카드 12개 이상 배치, 3열 이상 그리드", 0),
        ("사실은 통과", "배너와 필터 영역이 y축에서 겹침", 0),
        ("사실은 통과2", "배송비 항목은 3단계에서 표시됨", 0),
        ("판단은 검출", "버튼이 작동하지 않고 찾기 어렵다", 2),
        ("감정은 검출", "결제 절차가 너무 복잡하다", 2),
        ("평가는 검출", "링크 위치가 모호하다", 1),
    ]
    for name, text, want in cases:
        got = len(S._scan(text))
        check(name, got == want, "검출 %d건 (기대 %d)" % (got, want))

    # 실제 지도 항목 형태로도
    good = {"path": "/shop", "title": "상품 목록",
            "layout": "좌측 필터 영역, 우측 상품 그리드 3열",
            "elements": [{"name": "정렬 드롭다운", "type": "선택", "where": "우측 상단"}]}
    bad = dict(good, layout="좌측 필터가 너무 좁아 불편하다")
    check("정상 지도 항목 통과", S.validate_page(good) == [])

    # 금칙어 목록이 한국어라, 모델이 다른 언어로 새면 필터가 통째로 무력해진다.
    # 프로바이더를 바꿀 때(Qwen 등) 실제로 열리는 구멍이다.
    zh = dict(good, layout="左侧筛选区，右侧商品网格")
    check("중국어로 새면 검출", any("한국어가 아닌" in i for i in S.validate_page(zh)))
    en = dict(good, layout="Left filter panel, right product grid")
    check("통째로 영어면 검출", any("한글이 없음" in i for i in S.validate_page(en)))
    mixed = dict(good, layout="상단에 MOJI STORE 로고, 하단 SALE 배너")
    check("상품명 영어는 통과", S.validate_page(mixed) == [])
    check("오염된 지도 항목 검출", len(S.validate_page(bad)) >= 1)


# ── 2. URL 템플릿 정규화 ──────────────────────────────────────────

def test_template() -> None:
    print("\n── URL 템플릿 정규화 ──")
    t = discover.template_key
    check("id 는 상태로 접힘",
          t("http://x/a/product.html?id=7") == t("http://x/a/product.html?id=12"),
          t("http://x/a/product.html?id=7"))
    check("cat 도 상태로 접힘",
          t("http://x/a/list.html?cat=상의") == "/a/list.html")
    check("모르는 파라미터는 남김",
          t("http://x/a/list.html?debug=1") == "/a/list.html?debug=1")


# ── 3. 탐색 3층 + 측정 기준선 (브라우저 필요) ──────────────────────

# clean 은 결함이 없으므로 이 항목들이 전부 0이어야 한다.
ZERO_ON_CLEAN = ("occluded", "low_contrast", "keyboard_unreachable")


async def measure(page, variant: str) -> tuple[dict, list]:
    root = config.site_root(variant)
    found = await discover.discover(page, root, serve_root=config.DEFAULT_SERVE_ROOT)
    rows = []
    for t in found["targets"]:
        await page.goto(t["url"], wait_until="networkidle",
                        timeout=config.STEP_TIMEOUT_MS)
        snap = await take_snapshot(page)
        rows.append({
            "path": discover.rel_path(t["url"], root),
            "found_by": t["found_by"],
            "occluded": sum(1 for e in snap["elements"] if e["occluded"]),
            "low_contrast": sum(1 for e in snap["elements"]
                                if (e.get("contrast") or 99) < 3.0
                                and not e.get("disabled_attr")),
            "keyboard_unreachable": sum(1 for e in snap["elements"]
                                        if not e["keyboard_reachable"]),
            "body_contrast": snap["body_contrast"],
            "body_font_size": snap["body_font_size"],
        })
    return found, rows


async def test_browser() -> None:
    from playwright.async_api import async_playwright

    async with async_playwright() as pw:
        browser = await pw.chromium.launch()
        ctx = await browser.new_context(viewport=config.VIEWPORT)
        page = await ctx.new_page()

        try:
            await page.goto(config.site_url("clean"), timeout=8000)
        except Exception:
            print("\n서버가 없습니다. 먼저 띄우세요:")
            print("  cd C:\\Users\\kamdo\\AI_Testing && python -m http.server 8000")
            await browser.close()
            raise SystemExit(1)

        results = {}
        for variant in ("clean", "buggy"):
            print("\n── 탐색 3층: %s ──" % variant)
            found, rows = await measure(page, variant)
            results[variant] = rows
            c = found["counts"]
            check("%s 페이지 6종 발견" % variant, len(found["targets"]) == 6,
                  "링크 %d + 디렉터리 %d + 수동 %d" % (c["link"], c["dir"], c["extra"]))
            check("%s 디렉터리 층이 링크 사각지대를 메움" % variant, c["dir"] >= 1,
                  ", ".join(r["path"] for r in rows if r["found_by"] == "dir")
                  or "메운 것 없음")

        print("\n── 측정 기준선: clean 은 전부 0 ──")
        for r in results["clean"]:
            for k in ZERO_ON_CLEAN:
                check("clean %s %s=0" % (r["path"], k), r[k] == 0, "실제 %d" % r[k])
        check("clean 본문 대비 AA 통과",
              all(r["body_contrast"] >= 4.5 for r in results["clean"]),
              "%s:1" % results["clean"][0]["body_contrast"])
        check("clean 본문 폰트 >= 14px",
              all(r["body_font_size"] >= 14 for r in results["clean"]),
              "%spx" % results["clean"][0]["body_font_size"])

        print("\n── 결함 탐지: buggy 는 잡혀야 한다 ──")
        b = results["buggy"]
        check("buggy 본문 대비 미달 (D-05)",
              all(r["body_contrast"] < 4.5 for r in b), "%s:1" % b[0]["body_contrast"])
        check("buggy 본문 폰트 미달 (D-06)",
              all(r["body_font_size"] < 14 for r in b), "%spx" % b[0]["body_font_size"])
        check("buggy 저대비 요소 다수",
              sum(r["low_contrast"] for r in b) >= 50,
              "합계 %d개" % sum(r["low_contrast"] for r in b))
        prod = next((r for r in b if r["path"].startswith("/product")), None)
        check("buggy 상품페이지 가짜 버튼 검출 (D-10)",
              bool(prod) and prod["keyboard_unreachable"] >= 2,
              "키보드불가 %d개" % (prod["keyboard_unreachable"] if prod else -1))

        # occluded 는 로드 직후 스냅샷에서는 양쪽 다 0이라 '탐지기가 도는지'가
        # 증명되지 않는다. flawed 의 D-26(10초 후 자동 팝업, Critical)을 실제로
        # 기다렸다가 잡히는지 확인해야 이 지표가 의미를 갖는다.
        print("\n── 시간 의존 결함: D-26 자동 팝업 (11초 대기) ──")
        await page.goto(config.site_url("buggy"), wait_until="networkidle")
        before = await take_snapshot(page)
        await page.wait_for_timeout(11_000)
        after = await take_snapshot(page)
        occ_before = sum(1 for e in before["elements"] if e["occluded"])
        occ_after = sum(1 for e in after["elements"] if e["occluded"])
        check("로드 직후에는 팝업 없음", occ_before == 0, "가려짐 %d" % occ_before)
        check("11초 후 가림 발생 (D-26)", occ_after > 0,
              "가려짐 %d -> %d" % (occ_before, occ_after))
        close = [e for e in after["elements"]
                 if "닫기" in (e["text"] or "") or (e["text"] or "").strip() == "x"]
        check("닫기 버튼이 24px 미만 (D-26)",
              bool(close) and any(e["w"] < 24 or e["h"] < 24 for e in close),
              ", ".join("%s %dx%d" % (e["text"], e["w"], e["h"]) for e in close) or "못 찾음")

        print("\n── 대조: 같은 지표가 두 사이트를 가른다 ──")
        for k in ZERO_ON_CLEAN:
            cs = sum(r[k] for r in results["clean"])
            bs = sum(r[k] for r in results["buggy"])
            print("        %-22s clean=%-4d buggy=%-4d" % (k, cs, bs))

        await ctx.close()
        await browser.close()


# ── 5. 페르소나 조립 (브라우저 불필요) ─────────────────────────────

def test_persona() -> None:
    """여기서 보는 것은 '100명이 만들어진다'가 아니라 **100명이 서로 다른가**,
    그리고 **아무도 만나지 못하는 결함이 생기지 않는가**이다."""
    print("\n── 페르소나 조립 ──")

    goals = G.attach_seeds([dict(g) for g in G.MOCK_GOALS])
    paths = {"/index.html", "/list.html", "/cart.html", "/product.html?id=3",
             "/checkout.html", "/complete.html"}
    check("기본 목표 11개가 검사 통과", G.validate(goals, paths) == [],
          "%d건" % len(G.validate(goals, paths)))

    # 품절 상품(?id=7)은 지도에 대표로 실리지 않는다. 템플릿으로 접어 비교하지
    # 않으면 마찰을 일부러 만드는 목표가 검사기에 지워진다.
    off = [dict(goals[0], id="GX", start_path="/product.html?id=7")]
    check("템플릿 밖 상태 URL도 통과", G.validate(off, paths)[:1] == []
          or all("시작 경로" not in i for i in G.validate(off, paths)))
    gone = [dict(goals[0], id="GY", start_path="/returns.html")]
    check("없는 페이지는 거부", any("시작 경로" in i for i in G.validate(gone, paths)))

    leak = [dict(goals[0], id="GZ", text="결제 버튼이 작동하지 않는지 확인한다")]
    check("결함을 알려주는 목표는 거부", any("판단 표현" in i for i in G.validate(leak, paths)))

    people = PS.build(goals, n=config.N_PERSONAS)
    pairs = {(p["combo_index"], p["goal_id"]) for p in people}
    check("100명이 서로 다른 (조합, 목표)", len(pairs) == len(people),
          "고유 %d / 전체 %d" % (len(pairs), len(people)))

    longest = max(len(p["prompt"]) for p in people)
    check("프롬프트가 상한 이내", longest <= config.PROMPT_MAX_CHARS,
          "최장 %d자 (상한 %d)" % (longest, config.PROMPT_MAX_CHARS))
    check("배경 서사 없음", all("살" not in p["prompt"] and "직장" not in p["prompt"]
                            for p in people))

    # 10초 문턱: D-26 자동 팝업은 로드 10초 후에 뜬다.
    dwell10 = sum(1 for p in people if p["dwell_ms"] >= 10000)
    check("10초 이상 머무는 인원 존재 (D-26)", dwell10 > 0, "%d명" % dwell10)

    seeded = [p for p in people if p["seed_state"]]
    check("재방문자는 빈 장바구니로 시작하지 않음",
          all(p["seed_state"] for p in people if p["traits"]["visit"] == "returning"),
          "시딩 %d명" % len(seeded))
    check("시딩된 사람은 user_type=returning",
          all(p["user_type"] == "returning" for p in seeded))
    check("시딩된 사람 프롬프트에 '처음이다' 없음",
          all("이 사이트는 처음이다" not in p["prompt"] for p in seeded))
    check("서툰 사람에게 URL 직접입력 없음",
          all("goto" not in p["allowed_actions"]
              for p in people if p["traits"]["literacy"] == "novice"))

    # 장바구니 키가 변형마다 다르다. 페르소나에 키가 박혀 있으면 한쪽이
    # 조용히 빈 장바구니가 되고 유형 C 전부가 무력화된다.
    blob = repr(people)
    check("페르소나에 localStorage 키가 박히지 않음",
          "moji_cart" not in blob)
    check("변형별 장바구니 키가 갈림",
          config.cart_key("clean") != config.cart_key("buggy"))


# ── 6. 탐색 루프 (브라우저 불필요) ─────────────────────────────────

def _st(n, url, typ, target=None):
    return {"step": n, "thought": "t", "action": {"type": typ, "target": target},
            "outcome": {"url_after": url}, "blocked_action": None}


def test_explore() -> None:
    """루프가 언제 멈추는지가 곧 토큰이다. 못 멈추면 30스텝을 다 태운다."""
    print("\n── 탐색 루프 ──")

    a, b = "http://x/index.html", "http://x/cart.html"
    stuck = [_st(i, a, "click", "link_8") for i in range(1, 4)]
    check("제자리 반복을 잡는다", E.loop_detected(stuck, a))

    # A→B→A→B 왕복. 이걸 못 잡으면 종료 사유가 max_steps 로 찍혀
    # '스텝이 모자랐다'와 '길을 잃었다'가 구분되지 않는다.
    pong = []
    for i in range(3):
        pong.append(_st(i * 2 + 1, b, "click", "link_8"))
        pong.append(_st(i * 2 + 2, a, "click", "link_1"))
    check("왕복 반복을 잡는다", E.loop_detected(pong, a))

    walking = [_st(1, a, "click", "link_1"), _st(2, b, "click", "link_5"),
               _st(3, "http://x/product.html", "scroll", None)]
    check("정상 이동은 잡지 않는다", not E.loop_detected(walking, "http://x/product.html"))

    novice = {"allowed_actions": ["click", "scroll"], "prompt": "p"}
    check("허용 밖 행동은 막힌다",
          E.check_allowed({"type": "goto", "value": "/checkout.html"}, novice) is not None)
    check("허용된 행동은 통과", E.check_allowed({"type": "click"}, novice) is None)
    # 끝내겠다는 의사 표시는 목록과 무관하게 막을 수 없다.
    check("포기는 언제나 허용", E.check_allowed({"type": "give_up"}, novice) is None)

    many = [_st(i, a, "scroll") for i in range(1, 11)]
    lines = E.history_block(many).count(chr(10)) + 1
    check("이력은 최근 3스텝만", lines == config.HISTORY_WINDOW,
          "%d줄 (창 %d)" % (lines, config.HISTORY_WINDOW))


# ── 7. 답사 페르소나 (브라우저 불필요) ─────────────────────────────

def test_scout() -> None:
    """설명서 형식이 정적 답사기와 어긋나면 generate/run 을 둘 다 고쳐야 하고,
    두 답사기의 지도를 비교할 수도 없게 된다."""
    print("\n── 답사 페르소나 ──")

    snap = {"url": "http://localhost:8000/ux-testbed/clean/product.html?id=3",
            "title": "상품", "elements": []}
    rec = {"layout": "좌측 이미지, 우측 옵션 영역", "elements": [], "steps": None}
    entry = SC.page_entry(snap, rec, "http://localhost:8000/ux-testbed/clean", "scout")
    need = {"path", "template", "title", "found_by", "layout", "elements",
            "links_to", "steps"}
    check("설명서 형식이 정적 답사기와 같다", need <= set(entry))
    check("상태 쿼리는 템플릿에서 접힌다",
          entry["template"].endswith("/product.html"), entry["template"])
    check("경로에는 상태가 남는다", entry["path"] == "/product.html?id=3", entry["path"])

    ok, issues = SC.clean_record(rec)
    check("사실 기록은 통과", issues == [])
    bad = {"layout": "옵션이 너무 작아 불편하다", "elements": [], "steps": None}
    _, issues2 = SC.clean_record(bad)
    check("판단이 섞인 기록은 걸러진다", len(issues2) >= 1, "%d건" % len(issues2))
    check("성격은 있지만 목표는 없다",
          "성격" in SC.PERSONALITY or "눌러보는" in SC.PERSONALITY)


def main() -> int:
    print("답사기 스모크 테스트 (LLM 불필요)")
    test_filter()
    test_template()
    test_persona()
    test_explore()
    test_scout()
    asyncio.run(test_browser())
    print("\n" + "=" * 52)
    print("통과 %d / 실패 %d" % (len(PASS), len(FAIL)))
    if FAIL:
        for f in FAIL:
            print("  실패: %s" % f)
        return 1
    print("전부 통과.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
