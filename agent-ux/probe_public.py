"""남의 사이트에서도 되는지 실제로 확인한다 (LLM 안 씀).

우리 파이프라인이 테스트베드에서만 도는 물건인지, 아무 주소에나 붙일 수 있는
물건인지를 가른다. **LLM 을 부르지 않으므로 크레딧이 없어도 돌아간다** — 확인하려는
것은 판단력이 아니라 '눈'이기 때문이다: 화면을 읽어낼 수 있는가, 요소에 이름을
붙일 수 있는가, 대비·가려짐·키보드 접근을 계산할 수 있는가.

대상은 **자동화 연습용으로 공개된 사이트**와 로봇을 막지 않는 공개 문서 사이트만
고른다. 남의 장사하는 사이트를 두들기지 않는다.
"""
import argparse
import asyncio
import json
import sys
import time

from uxagent import config
from uxagent.snapshot import take_snapshot

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:  # noqa: BLE001
        pass

TARGETS = [
    ("자동화 연습용 쇼핑몰", "https://www.saucedemo.com/"),
    ("자동화 연습용 상품목록", "https://webscraper.io/test-sites/e-commerce/allinone"),
    ("실제 공개 문서(무거움)", "https://developer.mozilla.org/en-US/"),
    ("실제 한국어 위키", "https://ko.wikipedia.org/wiki/%EB%8C%80%ED%95%9C%EB%AF%BC%EA%B5%AD"),
]

# 사람 확인·차단벽에 흔히 나오는 말. 있으면 봇으로 걸린 것이다.
WALL = ["cloudflare", "captcha", "are you human", "access denied",
        "verify you are", "unusual traffic", "blocked"]


async def probe(page, name: str, url: str) -> dict:
    row = {"name": name, "url": url}
    t0 = time.time()
    try:
        resp = await page.goto(url, wait_until="domcontentloaded", timeout=45000)
        row["status"] = resp.status if resp else None
        row["final_url"] = page.url
        try:
            await page.wait_for_load_state("networkidle", timeout=12000)
        except Exception:  # noqa: BLE001
            row["note"] = "networkidle 미도달(계속 뭔가 불러오는 사이트)"
    except Exception as e:  # noqa: BLE001
        row["error"] = "%s: %s" % (type(e).__name__, str(e)[:90])
        return row
    row["load_s"] = round(time.time() - t0, 1)

    body = (await page.inner_text("body"))[:4000].lower()
    row["wall"] = next((w for w in WALL if w in body), None)

    t1 = time.time()
    try:
        snap = await take_snapshot(page)
    except Exception as e:  # noqa: BLE001
        row["snapshot_error"] = "%s: %s" % (type(e).__name__, str(e)[:90])
        return row
    row["snap_s"] = round(time.time() - t1, 1)

    els = snap["elements"]
    row["elements"] = len(els)
    # 이름 없는 요소는 에이전트가 지목할 수는 있어도 '무엇인지' 모른다.
    row["named"] = sum(1 for e in els if (e.get("text") or "").strip())
    row["low_contrast"] = sum(1 for e in els if e.get("contrast") is not None
                              and e["contrast"] < 4.5)
    row["occluded"] = sum(1 for e in els if e.get("occluded"))
    row["no_keyboard"] = sum(1 for e in els if e.get("keyboard") is False)
    row["page_h"] = snap.get("page_height")
    row["h_scroll"] = snap.get("horizontal_scroll")

    # 우리가 붙인 이름표가 실제로 다시 짚히는가 — 이게 되면 조작이 된다.
    sample = [e["id"] for e in els[:60]]
    hits = 0
    for aid in sample:
        try:
            if await page.locator('[data-agent-id="%s"]' % aid).count():
                hits += 1
        except Exception:  # noqa: BLE001
            pass
    row["reselect"] = "%d/%d" % (hits, len(sample))

    # 같은 사이트 안에서 갈 곳이 있는가 (탐색이 가능한가)
    host = page.url.split("/")[2] if "//" in page.url else ""
    links = await page.eval_on_selector_all(
        "a[href]", "els => els.map(e => e.href)")
    row["links_total"] = len(links)
    row["links_internal"] = sum(1 for h in links if host and host in h)

    # 로그인 벽인지
    row["login_form"] = bool(await page.locator(
        "input[type=password]").count())
    return row


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", action="append", help="직접 지정한 주소만 검사")
    args = ap.parse_args()
    targets = [("직접 지정", u) for u in args.url] if args.url else TARGETS

    from playwright.async_api import async_playwright
    rows = []
    async with async_playwright() as pw:
        browser = await pw.chromium.launch()
        ctx = await browser.new_context(
            viewport=config.VIEWPORT,
            # 기본 헤드리스 표식을 그대로 두면 실제보다 더 자주 막힌다.
            # 무엇에 막히는지 정확히 보려고 흔한 브라우저 표식을 쓴다.
            user_agent=("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/128.0.0.0 Safari/537.36"),
            locale="ko-KR",
        )
        page = await ctx.new_page()
        for name, url in targets:
            print("· %s  %s" % (name, url))
            row = await probe(page, name, url)
            rows.append(row)
            print("   ", json.dumps(row, ensure_ascii=False)[:300])
        await browser.close()

    print("\n" + "=" * 78)
    print("%-22s %-6s %-7s %-8s %-9s %-9s %s"
          % ("사이트", "응답", "요소", "이름있음", "다시짚기", "내부링크", "막힘"))
    for r in rows:
        print("%-22s %-6s %-7s %-8s %-9s %-9s %s" % (
            r["name"][:20], r.get("status", r.get("error", "?"))[:6]
            if isinstance(r.get("status", ""), str) else r.get("status", "-"),
            r.get("elements", "-"), r.get("named", "-"),
            r.get("reselect", "-"), r.get("links_internal", "-"),
            r.get("wall") or ("로그인벽" if r.get("login_form") else "없음")))
    with open("probe_public.json", "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=1)
    print("\n자세한 값: agent-ux/probe_public.json")


if __name__ == "__main__":
    asyncio.run(main())
