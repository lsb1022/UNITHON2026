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
from collections import Counter

sys.stdout.reconfigure(encoding="utf-8")

from uxagent import config, discover
from uxagent import explore as E
from uxagent import scout as SC
import generate as GEN
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
    """설계 지시(2026-08-25): 특성 4축 x 1~5단계, 목표는 하나.

    여기서 보는 것은 '100명이 만들어진다'가 아니라 **비교가 성립하는가**이다.
    분포가 기울면 "숙련도가 낮으면 어떤가"를 물을 때 표본 크기가 달라진다.
    """
    print("\n── 페르소나 조립 ──")

    goal = "코튼 셔츠를 장바구니에 담아 주문까지 마친다"
    people = PS.build(goal, "/index.html", n=config.N_PERSONAS)

    combos = {tuple(p["traits"][a] for a in PS.AXES) for p in people}
    check("100명이 서로 다른 4축 조합", len(combos) == len(people),
          "고유 %d / 전체 %d" % (len(combos), len(people)))

    for a in PS.AXES:
        c = Counter(p["traits"][a] for p in people)
        spread = max(c.values()) - min(c.values())
        check("%s 1~5단계가 고르게" % PS.AXIS_LABEL[a],
              set(c) == {1, 2, 3, 4, 5} and spread <= 1,
              " ".join("%d단계:%d" % (k, c[k]) for k in sorted(c)))

    dwell10 = [p for p in people if p["dwell_ms"] >= 10000]
    check("체류 10초 이상이 존재 (자동 팝업 조건)", len(dwell10) > 0, "%d명" % len(dwell10))
    check("체류 10초 이상은 주의 지속이 높은 사람",
          all(p["traits"]["attention"] >= 4 for p in dwell10))

    novice = [p for p in people if p["traits"]["literacy"] <= 2]
    check("숙련도 1-2 는 주소창 금지",
          all(PS.URL_ACTION not in p["allowed_actions"] for p in novice),
          "%d명" % len(novice))
    check("숙련도 1-2 는 검색 금지",
          all(not p["search_allowed"] for p in novice))
    check("숙련도 4-5 는 주소창 허용",
          all(PS.URL_ACTION in p["allowed_actions"]
              for p in people if p["traits"]["literacy"] >= 4))

    # 탐색 범위는 '거쳐가는 화면 수'가 아니라 '대안을 몇 개 보는가'다.
    # 경로를 막으면 목표 자체가 불가능해져 그 사람들의 결과가 사이트와 무관해진다.
    narrow = [p for p in people if p["traits"]["breadth"] <= 2]
    check("탐색 범위 1-2 는 비교 개수 제한",
          all(p["compare_cap"] == PS.COMPARE_CAP[p["traits"]["breadth"]]
              for p in narrow), "%d명" % len(narrow))
    check("탐색 범위 1 은 대안 1개만", all(p["compare_cap"] == 1 for p in people
                                    if p["traits"]["breadth"] == 1))
    check("탐색 범위 3 이상은 제한 없음",
          all(not p["compare_cap"] for p in people if p["traits"]["breadth"] >= 3))
    check("경로 자체는 막지 않는다 (page_cap 폐기)", "page_cap" not in people[0])

    check("인내심이 낮을수록 스텝이 적다",
          all(p["max_steps"] <= q["max_steps"] for p in people for q in people
              if p["traits"]["patience"] < q["traits"]["patience"]))

    longest = max(len(p["prompt"]) for p in people)
    check("프롬프트가 상한 이내", longest <= config.PROMPT_MAX_CHARS,
          "최장 %d자 (상한 %d)" % (longest, config.PROMPT_MAX_CHARS))
    check("배경 서사 없음", all("살" not in p["prompt"] and "직장" not in p["prompt"]
                            for p in people))
    check("목표는 사람마다 복사되지 않는다", "goal" not in people[0],
          "페르소나 항목의 키: %s" % ",".join(sorted(people[0])[:6]))

    # 목표 문자열도 답사자와 같은 필터를 통과해야 한다.
    site_map = {"pages": [{"path": "/index.html", "title": "MOJI STORE",
                           "layout": "상단 헤더, 상품 그리드",
                           "elements": [{"name": "장바구니", "where": "우측 상단"}]}]}
    ok, warns = GEN.check_goal("코튼 셔츠를 장바구니에 담아 주문까지 마친다", site_map)
    check("정상 목표는 통과", ok == [])
    bad, _ = GEN.check_goal("결제 버튼이 작동하지 않는지 확인한다", site_map)
    check("결함을 알려주는 목표는 거부", any("판단 표현" in x for x in bad))
    zh, _ = GEN.check_goal("把商品加入购物车并完成结算", site_map)
    check("한국어가 아닌 목표는 거부", any("한국어가 아닌" in x for x in zh))
    _, w = GEN.check_goal("반품 신청서를 작성한다", site_map)
    check("지도에 없는 기능은 경고", any("확인되지 않은" in x for x in w))


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

    # 이력은 '맨 앞 + 최근'이다. 뒤에서만 자르면 목표를 이룬 결정적 행동이
    # 먼저 밀려나 맴돌이가 난다 (실측: G11 목표 4명 전원 맴돌이).
    many = [_st(i, a, "click", "b%d" % i) for i in range(1, 21)]
    txt = E.history_block(many)
    lines = txt.count(chr(10)) + 1
    cap = config.HISTORY_HEAD + config.HISTORY_WINDOW + 1   # +1 은 '생략' 줄
    check("이력 길이가 상한 이내", lines <= cap, "%d줄 (상한 %d)" % (lines, cap))
    check("맨 앞 스텝은 항상 남는다", txt.startswith("1. "))
    check("최근 스텝도 남는다", "20." in txt)
    check("가운데는 접힌다", "생략" in txt)
    check("짧으면 통째로 보여준다",
          E.history_block(many[:3]).count(chr(10)) + 1 == 3)


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
