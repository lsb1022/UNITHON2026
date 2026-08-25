"""프롬프트 내시경 — 페르소나가 실제로 받는 글자를 그대로 보여준다.

    python show-prompt.py                                  # P001 이 buggy 첫 화면에서 받는 것
    python show-prompt.py --persona P044 --path /cart.html
    python show-prompt.py --variant clean --no-map         # 지도 없는 대조군은 뭘 받나
    python show-prompt.py --breakdown                      # 어느 부분이 몇 토큰인지만

프롬프트가 코드 안에만 있으면 아무도 검토하지 못한다. 비용의 3분의 2가
화면 요소 목록이라는 것도, 그걸 눈으로 봐야 알 수 있다.

LLM 을 호출하지 않는다. 브라우저만 띄워 화면을 재고 조립까지만 한다.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:  # noqa: BLE001
        pass

from uxagent import config, explore
from uxagent.snapshot import render_for_prompt, take_snapshot
from uxagent.survey import get_map_slice

# 한글이 섞인 글을 토큰으로 어림하는 계수. 정확한 값은 프로바이더마다 다르므로
# '대략'이라고 말하기 위한 눈금일 뿐이다. 실제 값은 실행 후 usage 에 찍힌다.
CHARS_PER_TOKEN = 1.7


def approx(text: str) -> int:
    return int(len(text) / CHARS_PER_TOKEN)


async def build(args) -> tuple[dict, str, str, dict]:
    from playwright.async_api import async_playwright

    pf = os.path.join(config.PERSONAS_DIR, "personas.json")
    with open(pf, encoding="utf-8") as f:
        people = json.load(f)["personas"]
    person = next((p for p in people if p["id"] == args.persona), people[0])

    root = config.site_root(args.variant, args.base)
    site_map = None
    if not args.no_map:
        mp = os.path.join(config.MAPS_DIR, "site_map_%s.json" % args.variant)
        with open(mp, encoding="utf-8") as f:
            site_map = json.load(f)

    path = args.path or person["start_path"]
    async with async_playwright() as pw:
        browser = await pw.chromium.launch()
        ctx = await browser.new_context(viewport=config.VIEWPORT)
        page = await ctx.new_page()
        await page.goto(root.rstrip("/") + "/" + path.lstrip("/"),
                        timeout=config.STEP_TIMEOUT_MS)
        if args.dwell:
            await asyncio.sleep(person["dwell_ms"] / 1000)
        snap = await take_snapshot(page)
        slice_ = get_map_slice(site_map, page.url, root) if site_map else None
        user = explore.build_user(person, snap, [], slice_)
        await browser.close()
    return person, explore.SYSTEM, user, {"snap": snap, "slice": slice_}


def breakdown(person: dict, system: str, user: str, extra: dict) -> None:
    snap, slice_ = extra["snap"], extra["slice"]
    els = render_for_prompt(snap, config.PROMPT_ELEMENT_LIMIT)
    slice_txt = "" if not slice_ else (
        "배치: %s\n요소: %s" % (slice_.get("layout"),
                              ", ".join(e.get("name", "?") for e in
                                        (slice_.get("elements") or [])[:10])))
    rows = [
        ("시스템 프롬프트 (매 호출 동일)", system),
        ("페르소나 + 목표", person["prompt"]),
        ("지도 슬라이스 (답사자가 쓴 것)", slice_txt),
        ("화면 요소 목록 (상한 %d개)" % config.PROMPT_ELEMENT_LIMIT, els),
    ]
    total = len(system) + len(user)
    print("\n" + "=" * 62)
    print("  프롬프트 구성 — %s / %s" % (person["id"], snap["url"].split("/")[-1]))
    print("=" * 62)
    for name, txt in rows:
        share = (len(txt) / total * 100) if total else 0
        print("  %-30s %6d자  ≈%5d토큰  %4.1f%%" % (name, len(txt), approx(txt), share))
    print("  " + "-" * 58)
    print("  %-30s %6d자  ≈%5d토큰" % ("합계 (시스템+사용자)", total, approx(total * "x")))
    print("\n  화면 요소 %d개 중 접힘선 아래 %d개. 상한을 넘는 %d개는 잘린다."
          % (len(snap["elements"]),
             sum(1 for e in snap["elements"] if e["below_fold"]),
             max(0, len(snap["elements"]) - config.PROMPT_ELEMENT_LIMIT)))
    p = config.price_of(config.model("explore"), config.role_provider("explore"))
    tok = approx(system + user)
    print("  이 화면에서 한 스텝의 입력 비용 ≈ $%.5f  (입력 $%.2f/1M 기준)"
          % (tok / 1_000_000 * p["input"], p["input"]))


def main() -> int:
    ap = argparse.ArgumentParser(description="페르소나가 받는 프롬프트를 그대로 출력")
    ap.add_argument("--variant", default="buggy", choices=sorted(config.SITE_DIRS))
    ap.add_argument("--base", default=config.DEFAULT_BASE)
    ap.add_argument("--persona", default="P001")
    ap.add_argument("--path", default="", help="볼 화면. 기본은 그 사람의 시작 화면")
    ap.add_argument("--no-map", action="store_true", help="지도 없는 대조군 조건")
    ap.add_argument("--dwell", action="store_true",
                    help="그 사람의 체류 시간만큼 기다렸다가 잰다 (자동 팝업 재현)")
    ap.add_argument("--breakdown", action="store_true", help="구성 비율만 보고 끝")
    args = ap.parse_args()

    person, system, user, extra = asyncio.run(build(args))

    if not args.breakdown:
        print("=" * 62)
        print("  %s  %s" % (person["id"], person.get("label", "")))
        print("  허용 행동: %s / 최대 %d스텝 / 체류 %dms"
              % (",".join(person["allowed_actions"]), person["max_steps"],
                 person["dwell_ms"]))
        print("=" * 62)
        print("\n───────── 시스템 프롬프트 (역할 지시, 매 호출 동일) ─────────\n")
        print(system)
        print("\n───────── 사용자 메시지 (스텝마다 새로 조립) ─────────\n")
        print(user)

    breakdown(person, system, user, extra)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
