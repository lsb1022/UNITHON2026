"""화면 6종을 **전체 페이지**로 한 장씩 찍어둔다 (LLM 안 씀).

히트맵의 배경이 될 사진이다. 답사자가 남긴 shots/ 는 1280x800 뷰포트만 담고
있어서 접힌 선 아래 클릭이 사진 밖으로 나간다 — 정상판은 클릭의 절반이
거기 있었다. 그래서 페이지 전체를 다시 찍는다.

팝업은 일부러 피한다. 결함판의 이메일 팝업은 10초 뒤에 떠서 화면을 덮는데,
그게 덮인 사진 위에 클릭을 얹으면 아래 무엇을 누르려 했는지가 안 보인다.
팝업 자체는 페르소나 기록에 남아 있으니 사진은 바닥 화면을 담는다.
"""
import asyncio
import json
import os
import sys

from uxagent import config

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:  # noqa: BLE001
        pass

# 지도의 대표 주소. 상품 상세는 ?id=1 하나로 고정한다 — 셔츠든 바지든
# 배치가 같아서 좌표가 통한다.
# 장바구니가 비어 있으면 장바구니·결제·완료 화면이 짧은 빈 화면으로 찍힌다.
# 페르소나는 물건을 담은 뒤에 그 화면에 갔으므로, 그 상태로 찍어야 좌표가 맞는다
# (정상판 결제 화면은 빈 상태 842px, 담은 상태 2600px — 클릭의 대부분이 그 밑에 있었다).
PAGES = [("index.html", False), ("list.html", False), ("product.html?id=1", False),
         ("cart.html", True), ("checkout.html", True), ("complete.html", True)]
OUT = os.path.join("..", "web", "public", "screens")


async def shoot(variant: str) -> list[dict]:
    from playwright.async_api import async_playwright

    root = config.site_root(variant).rstrip("/") + "/"
    folder = os.path.join(OUT, variant)
    os.makedirs(folder, exist_ok=True)
    rows = []

    async with async_playwright() as pw:
        browser = await pw.chromium.launch()
        ctx = await browser.new_context(viewport=config.VIEWPORT)
        page = await ctx.new_page()
        for spec, needs_cart in PAGES:
            key = spec.split("?")[0]
            if needs_cart:
                # 사이트가 쓰는 함수를 그대로 불러 담는다. 손으로 만든 객체를
                # 넣으면 사이트가 기대하는 모양과 어긋나도 알 수가 없다.
                await page.goto(root + "product.html?id=1", wait_until="networkidle")
                await page.evaluate(
                    "() => addToCart({ id: 1, color: '아이보리', size: 'M', qty: 1 })")
            await page.goto(root + spec, wait_until="networkidle")
            # 이미지가 자리를 잡아야 높이가 확정된다. 팝업(10초)보다는 훨씬 이르다.
            await page.wait_for_timeout(600)
            height = await page.evaluate(
                "() => Math.max(document.documentElement.scrollHeight, document.body.scrollHeight)")
            name = key.replace(".html", "") + ".jpg"
            await page.screenshot(path=os.path.join(folder, name),
                                  full_page=True, type="jpeg", quality=82)
            size = os.path.getsize(os.path.join(folder, name))
            rows.append({"key": key, "file": "%s/%s" % (variant, name),
                         "w": config.VIEWPORT["width"], "h": height, "bytes": size})
            print("  %-14s %4dx%-5d %5.0fKB" % (key, config.VIEWPORT["width"], height, size / 1024))
        await browser.close()
    return rows


async def main() -> None:
    index = {}
    for variant in ("clean", "buggy"):
        print("[%s]" % variant)
        index[variant] = await shoot(variant)
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "index.json"), "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=1)
    total = sum(r["bytes"] for v in index.values() for r in v)
    print("\n%d장 / 합계 %.1fMB → %s" % (
        sum(len(v) for v in index.values()), total / 1048576, OUT))


if __name__ == "__main__":
    asyncio.run(main())
