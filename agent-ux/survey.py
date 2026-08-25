"""답사기 CLI — 사이트 지도를 1회 만들어 저장한다.

    python survey.py --variant buggy
    python survey.py --variant clean
    python survey.py --variant buggy --mock --yes

한 번 저장하면 재사용한다. 100명 돌릴 때마다 다시 하지 않는다.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from datetime import datetime

# Windows 콘솔 기본 코드페이지(cp949)에서 한글이 깨진다. 출력만 UTF-8로 고정.
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:  # noqa: BLE001 - 리다이렉트된 스트림이면 무시
        pass

from uxagent import config, discover
from uxagent import survey as S
from uxagent.llm import Usage, build_client

SRC_LABEL = {"link": "링크", "dir": "디렉터리", "extra": "수동"}


def print_map(site_map: dict, meas: list) -> None:
    print("\n" + "=" * 62)
    print("  지도: %s   페이지 %d종" % (site_map["variant"], len(site_map["pages"])))
    print("=" * 62)
    by_path = {m["path"]: m for m in meas}
    for p in site_map["pages"]:
        print("\n[%s] %s   (발견: %s)" % (p["path"], p["title"], SRC_LABEL[p["found_by"]]))
        print("  배치: %s" % p["layout"])
        names = ", ".join(e.get("name", "?") for e in p["elements"][:8])
        print("  요소: %s%s" % (names, " …" if len(p["elements"]) > 8 else ""))
        if p.get("steps"):
            print("  단계: %s" % json.dumps(p["steps"], ensure_ascii=False))
        m = by_path.get(p["path"])
        if m:
            print("  (참고·코드 계산) 요소 %d개 / 접힘선아래 %d / 가려짐 %d / 저대비 %d / "
                  "키보드불가 %d / 본문대비 %s:1 %spx%s"
                  % (m["element_count"], m["below_fold"], m["occluded"],
                     m["low_contrast"], m["keyboard_unreachable"],
                     m["body_contrast"], m["body_font_size"],
                     " / 가로스크롤" if m["horizontal_scroll"] else ""))
    print("\n" + "-" * 62)
    print("참고 수치는 지도에 저장되지 않습니다. snapshot.py가 매 스텝 다시 계산하며,")
    print("페르소나 프롬프트에는 위 '배치'와 '요소' 서술만 들어갑니다.")
    print("-" * 62)


async def run(args) -> int:
    from playwright.async_api import async_playwright

    # 우리 테스트베드의 한 벌이거나, 사용자가 준 아무 공개 주소거나.
    target = config.resolve_target(
        None if args.url else args.variant, args.url, args.base)
    root = target["root"]
    stem = config.map_stem(target)
    # 답사자가 본 화면을 남길 곳. 사이트마다 따로 쌓는다.
    shots_dir = args.shots_dir or os.path.join("shots", stem)
    usage = Usage()
    pname = config.role_provider("survey")
    client = None if args.mock else build_client(pname)
    model = config.model("survey", pname)

    async with async_playwright() as pw:
        browser = await pw.chromium.launch()
        ctx = await browser.new_context(viewport=config.VIEWPORT)
        page = await ctx.new_page()

        print("답사 대상: %s" % root)
        if not args.mock:
            print("프로바이더: %s / 모델: %s" % (pname, model))

        found = await discover.discover(
            page, root,
            # 로컬 정적 사이트일 때만 파일시스템을 뒤져 링크가 못 간 페이지를
            # 찾는다. 남의 사이트에는 그럴 디렉터리가 없다 — 링크만 따라간다.
            serve_root=(None if (args.no_local_dir or target["kind"] == "url")
                        else args.serve_root),
            extra=args.extra,
            start=target["start"],
            max_pages=args.max_pages,
        )
        c = found["counts"]
        print("발견: 링크 %d종 + 디렉터리 %d종 + 수동 %d종 = %d종%s"
              % (c["link"], c["dir"], c["extra"], len(found["targets"]),
                 "" if found["local_dir_used"] else "  (로컬 디렉터리 층 꺼짐)"))
        for t in found["targets"]:
            if t["found_by"] == "dir":
                print("  ! %s 는 inbound <a>가 없어 링크 추적으로는 도달 불가 "
                      "— 디렉터리 목록으로 보강" % discover.rel_path(t["url"], root))

        pages, meas = [], []
        for i, t in enumerate(found["targets"], 1):
            path = discover.rel_path(t["url"], root)
            print("  [%d/%d] %s …" % (i, len(found["targets"]), path), flush=True)

            entry, m = await S.survey_page(
                page, t, root, client=client, model=model,
                shots_dir=shots_dir, usage=usage, mock=args.mock,
                edges=found["edges"])

            # 판단 표현이 섞이면 재생성. LLM에게 자기 검증을 맡기지 않는다.
            ok = True
            for attempt in range(1, config.SURVEY_VALIDATE_RETRIES + 1):
                issues = S.validate_page(entry)
                if not issues:
                    break
                print("      판단 표현 %d건 → 재생성 %d회차" % (len(issues), attempt))
                for it in issues[:5]:
                    print("        - %s" % it)
                entry, m = await S.survey_page(
                    page, t, root, client=client, model=model,
                    shots_dir=shots_dir, usage=usage, mock=args.mock,
                    edges=found["edges"])
            else:
                if S.validate_page(entry):
                    ok = False

            if not ok:
                print("      %d회 재생성에도 판단 표현이 남았습니다: %s"
                      % (config.SURVEY_VALIDATE_RETRIES, path))
                print("      지도를 저장하지 않고 중단합니다. 프롬프트를 손봐야 합니다.")
                await browser.close()
                return 2

            pages.append(entry)
            meas.append(m)

        await ctx.close()
        await browser.close()

    site_map = {
        "variant": stem,
        "target_url": target["start"],
        "target_kind": target["kind"],
        "root": root,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "pages": pages,
        # 답사가 못 간 곳을 못 갔다고 말하는 것이 이 도구의 신뢰 논리다.
        # 페르소나 실행 중 map_miss로 잡힌 URL을 여기에 채워 2회차에 보강한다.
        "unreached": [],
        "structure": " → ".join(p["title"] for p in pages),
    }

    issues = S.validate_map(site_map)
    if issues:
        print("\n지도 전체 검사에서 %d건: %s" % (len(issues), issues[:5]))
        return 2

    print_map(site_map, meas)

    if not args.yes:
        ans = input("\n판단이 섞인 문장이 있습니까? [없음=엔터 / 편집=e / 중단=q] ").strip().lower()
        if ans == "q":
            print("저장하지 않고 중단했습니다.")
            return 1
        if ans == "e":
            print("저장 후 파일을 직접 여세요. 편집 뒤 다시 검사하려면:")
            print("  python survey.py --variant %s --validate-only" % args.variant)

    os.makedirs(config.MAPS_DIR, exist_ok=True)
    mp = os.path.join(config.MAPS_DIR, "site_map_%s.json" % stem)
    with open(mp, "w", encoding="utf-8") as f:
        json.dump(site_map, f, ensure_ascii=False, indent=2)

    meta = {
        "variant": stem,
        "target_url": target["start"],
        "generated_at": site_map["generated_at"],
        "provider": None if args.mock else pname,
        "model": None if args.mock else model,
        "mock": args.mock,
        "viewport": config.VIEWPORT,
        "pages": len(pages),
        "shots_dir": shots_dir,
        "discovery": found["counts"],
        "usage": usage.as_dict(),
        # 프롬프트에 절대 들어가지 않는 참고용 수치. clean/buggy 대조와
        # 사람 확인 화면에만 쓴다.
        "reference_measurements": meas,
    }
    mmp = os.path.join(config.MAPS_DIR, "survey_meta_%s.json" % stem)
    with open(mmp, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    u = meta["usage"]
    print("\n저장: %s" % mp)
    print("      %s" % mmp)
    print("호출 %d회 / 입력 %d · 출력 %d 토큰 / 약 $%s"
          % (u["calls"], u["tokens_in"], u["tokens_out"], u["cost_usd"]))
    return 0


def validate_only(variant: str) -> int:
    mp = os.path.join(config.MAPS_DIR, "site_map_%s.json" % variant)
    with open(mp, encoding="utf-8") as f:
        site_map = json.load(f)
    issues = S.validate_map(site_map)
    if issues:
        print("판단 표현 %d건:" % len(issues))
        for it in issues:
            print("  - %s" % it)
        return 2
    print("%s: 판단 표현 없음. 페이지 %d종." % (mp, len(site_map["pages"])))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="답사 에이전트 — 사이트 지도 생성")
    ap.add_argument("--variant", default="buggy", choices=sorted(config.SITE_DIRS))
    ap.add_argument("--shots-dir", default="",
                    help="답사자가 본 화면을 저장할 곳. 기본 shots/<사이트>/")
    ap.add_argument("--url", default="",
                    help="우리 테스트베드가 아닌 아무 공개 주소. 주면 --variant 는 무시된다.")
    ap.add_argument("--base", default=config.DEFAULT_BASE,
                    help="정적 서버 루트. 포트 분리 없이 경로로 clean/flawed를 가른다")
    ap.add_argument("--serve-root", default=config.DEFAULT_SERVE_ROOT,
                    help="http.server를 띄운 로컬 디렉터리 (2층 보강용)")
    ap.add_argument("--no-local-dir", action="store_true",
                    help="디렉터리 목록 층을 끈다 (남의 사이트와 동일 조건으로 테스트)")
    ap.add_argument("--extra", action="append", default=[],
                    help="수동 추가 URL. 반복 지정 가능")
    ap.add_argument("--max-pages", type=int, default=config.SURVEY_MAX_PAGES)
    ap.add_argument("--mock", action="store_true", help="LLM 없이 파이프라인만 확인")
    ap.add_argument("--yes", action="store_true", help="사람 확인 단계 생략")
    ap.add_argument("--validate-only", action="store_true",
                    help="저장된 지도의 판단 표현만 다시 검사")
    args = ap.parse_args()

    if args.validate_only:
        return validate_only(args.variant)
    return asyncio.run(run(args))


if __name__ == "__main__":
    raise SystemExit(main())
