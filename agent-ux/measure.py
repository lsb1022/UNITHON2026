"""계산된 시각 정보를 눈으로 본다 — 어떤 화면이든 재서 표로 뿌린다.

    python measure.py --variant buggy --path /product.html?id=1
    python measure.py --variant clean --path /index.html --dwell 12
    python measure.py --variant buggy --path /list.html --csv out.csv
    python measure.py --compare /index.html          # clean vs buggy 나란히

이 값들이 페르소나에게 스크린샷 대신 들어가는 것이다. 브라우저가 레이아웃
단계에서 이미 계산해둔 것을 그대로 읽으므로 추정이 아니라 측정이다.

  대비        WCAG 공식 그대로. 배경이 투명하면 조상으로 올라가 실제 색을 찾는다
  가려짐      요소 중심점에서 히트 테스트. 다른 것이 잡히면 가려진 것이다
  접힘선      fold_y 기준. 스크롤 없이 보이는지
  키보드도달  tabindex 와 태그 종류로 판정

LLM 을 부르지 않는다. 돈이 들지 않는다.
"""
from __future__ import annotations

import argparse
import asyncio
import csv
import json
import sys

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:  # noqa: BLE001
        pass

from uxagent import config
from uxagent.snapshot import take_snapshot

FIELDS = ["id", "tag", "text", "page_x", "page_y", "w", "h", "below_fold",
          "occluded", "contrast", "font_size", "keyboard_reachable",
          "disabled_look", "disabled_attr", "input_type", "value", "checked"]


def clean_path(path: str) -> str:
    """Git Bash 는 "/index.html" 같은 인자를 윈도우 경로로 바꿔버린다
    ("C:/Program Files/Git/index.html"). 마지막 조각만 남겨 되돌린다."""
    if ":" in path and "/" in path:
        return "/" + path.rsplit("/", 1)[-1]
    return path


async def measure(variant: str, path: str, base: str, dwell: float,
                  url: str = "") -> dict:
    """URL 하나만 있으면 잰다.

    HTML 파일도, 저장소 접근도 필요 없다. 브라우저가 렌더링을 끝낸 뒤의
    DOM/CSSOM 을 읽으므로, 방문한 사람의 브라우저가 아는 것만 쓴다.
    """
    from playwright.async_api import async_playwright

    root = "" if url else config.site_root(variant, base)
    async with async_playwright() as pw:
        browser = await pw.chromium.launch()
        ctx = await browser.new_context(viewport=config.VIEWPORT)
        page = await ctx.new_page()
        dest = url or (root.rstrip("/") + "/" + clean_path(path).lstrip("/"))
        await page.goto(dest, timeout=config.STEP_TIMEOUT_MS)
        if dwell:
            await asyncio.sleep(dwell)
        snap = await take_snapshot(page)
        await browser.close()
    return snap


def flags(e: dict) -> str:
    """사람이 겪을 마찰만 짧게. 프롬프트에 들어가는 것과 같은 규칙이다."""
    f = []
    if e["below_fold"]:
        f.append("접힘아래")
    if e["occluded"]:
        f.append("가려짐")
    if e["disabled_look"]:
        f.append("비활성처럼")
    c = e.get("contrast")
    if c is not None and c < 3.0 and not e.get("disabled_attr"):
        f.append("저대비")
    if e["w"] * e["h"] > 0 and (e["w"] < 24 or e["h"] < 24):
        f.append("작음")
    if not e["keyboard_reachable"]:
        f.append("키보드X")
    return ",".join(f)


def table(snap: dict, limit: int) -> None:
    print("  %-9s %-22s %9s %8s %6s %5s  %s"
          % ("이름", "글자", "위치", "크기", "대비", "폰트", "마찰"))
    print("  " + "-" * 74)
    for e in snap["elements"][:limit]:
        txt = (e["text"] or "")[:20]
        print("  %-9s %-22s %4d,%-4d %4dx%-3d %6s %4spx  %s"
              % (e["id"], txt, e["page_x"], e["page_y"], e["w"], e["h"],
                 e["contrast"] if e["contrast"] is not None else "-",
                 e["font_size"], flags(e)))
    if len(snap["elements"]) > limit:
        print("  … 외 %d개 (--limit 로 더 보기)" % (len(snap["elements"]) - limit))


def summary(snap: dict) -> dict:
    els = snap["elements"]
    return {
        "요소": len(els),
        "접힘선아래": sum(1 for e in els if e["below_fold"]),
        "가려짐": sum(1 for e in els if e["occluded"]),
        "저대비": sum(1 for e in els
                   if (e.get("contrast") or 99) < 3.0 and not e.get("disabled_attr")),
        "작음": sum(1 for e in els if e["w"] * e["h"] > 0 and (e["w"] < 24 or e["h"] < 24)),
        "키보드불가": sum(1 for e in els if not e["keyboard_reachable"]),
    }


def head(snap: dict) -> None:
    print("=" * 78)
    print("  %s" % snap["url"])
    print("  본문 대비 %s:1 / 본문 %spx / 문서 높이 %dpx / 접힘선 %dpx%s"
          % (snap["body_contrast"], snap["body_font_size"], snap["page_height"],
             snap["fold_y"], " / 가로 스크롤 발생" if snap["horizontal_scroll"] else ""))
    print("  " + "  ".join("%s %d" % (k, v) for k, v in summary(snap).items()))
    print("=" * 78)


def main() -> int:
    ap = argparse.ArgumentParser(description="계산된 시각 정보 보기 (LLM 불필요)")
    ap.add_argument("--variant", default="buggy", choices=sorted(config.SITE_DIRS))
    ap.add_argument("--base", default=config.DEFAULT_BASE)
    ap.add_argument("--path", default="/index.html")
    ap.add_argument("--dwell", type=float, default=0,
                    help="이만큼 기다렸다 잰다. 12를 주면 자동 팝업이 뜬 뒤를 본다")
    ap.add_argument("--limit", type=int, default=30)
    ap.add_argument("--json", default="", help="원본 스냅샷을 이 파일로 저장")
    ap.add_argument("--csv", default="", help="요소 표를 CSV 로 저장 (엑셀에서 열기)")
    ap.add_argument("--url", default="",
                    help="임의의 주소를 직접 잰다. 우리 테스트베드가 아니어도 된다")
    ap.add_argument("--compare", default="",
                    help="이 경로를 clean/buggy 양쪽에서 재서 나란히 비교")
    args = ap.parse_args()

    if args.compare:
        rows = {}
        for v in ("clean", "buggy"):
            snap = asyncio.run(measure(v, clean_path(args.compare), args.base, args.dwell))
            rows[v] = summary(snap)
            rows[v]["본문대비"] = snap["body_contrast"]
            rows[v]["본문폰트"] = snap["body_font_size"]
        print("=" * 56)
        print("  %s   (%s초 대기)" % (args.compare, args.dwell))
        print("=" * 56)
        print("  %-12s %10s %10s" % ("", "clean", "buggy"))
        for k in rows["clean"]:
            print("  %-12s %10s %10s" % (k, rows["clean"][k], rows["buggy"][k]))
        return 0

    snap = asyncio.run(measure(args.variant, args.path, args.base, args.dwell, args.url))
    head(snap)
    table(snap, args.limit)

    if args.json:
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump(snap, f, ensure_ascii=False, indent=1)
        print("\n원본 저장: %s" % args.json)
    if args.csv:
        with open(args.csv, "w", encoding="utf-8-sig", newline="") as f:
            w = csv.DictWriter(f, fieldnames=FIELDS, extrasaction="ignore")
            w.writeheader()
            for e in snap["elements"]:
                w.writerow(e)
        print("표 저장: %s  (엑셀에서 바로 열립니다)" % args.csv)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
