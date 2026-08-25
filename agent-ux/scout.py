"""답사 페르소나 CLI — 스크린샷을 찍어가며 직접 조작해 설명서를 만든다.

    python scout.py --variant clean --mock --yes
    python scout.py --variant clean --headed        # 돌아다니는 걸 눈으로 보며
    python scout.py --variant buggy --max-steps 60

`survey.py`(정적 촬영)와 결과 파일이 **같은 형식**이라 뒤따르는
generate.py / run.py 는 아무것도 고칠 필요가 없다. 두 답사기의 지도를
바꿔 넣어가며 비교할 수도 있다.

차이는 도달 범위다. 정적 촬영은 `<a href>` 로 갈 수 있는 곳만 찍는다.
이쪽은 실제로 담고 결제를 진행하므로 **눌러야 나오는 화면**이 설명서에 들어간다.

이미지 호출은 페르소나 한 명분(스텝 수만큼)이다. 뒤따르는 100명은 이
설명서만 읽고 이미지를 한 장도 쓰지 않는다.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import shutil
import sys
from datetime import datetime

# Windows 콘솔 기본 코드페이지(cp949)에서 한글이 깨진다. 출력만 UTF-8로 고정.
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:  # noqa: BLE001 - 리다이렉트된 스트림이면 무시
        pass

from uxagent import config, discover, explore, scout as S
from uxagent import survey as SV
from uxagent.llm import Usage, build_client
from uxagent.snapshot import render_for_prompt, take_snapshot


def history_line(steps: list[dict]) -> str:
    out = []
    for s in steps[-config.HISTORY_WINDOW:]:
        a = s["action"]
        tgt = (" " + a["target"]) if a.get("target") else ""
        out.append("%d. %s → %s%s%s" % (s["n"], s["thought"][:50], a["type"], tgt,
                                        "  (%s)" % s["note"] if s["note"] else ""))
    return "\n".join(out)


async def run(args) -> int:
    from playwright.async_api import async_playwright

    root = config.site_root(args.variant, args.base)
    usage = Usage()
    pname = config.role_provider("survey")
    client = None if args.mock else build_client(pname)
    model_list = config.models("survey", pname)
    model = model_list[0]

    print("=" * 62)
    print("  답사 페르소나 — %s" % root)
    print("  최대 %d스텝 / 새 화면이 %d스텝 연속 없으면 종료%s"
          % (args.max_steps, args.dry_rounds, "   [모의]" if args.mock else ""))
    if not args.mock:
        print("  %s / %s (+대체 %d개) / 이미지 최대 %d회 / 상한 $%s"
              % (pname, model, len(model_list) - 1, args.max_steps, args.max_usd))
    print("=" * 62)

    pages: dict[str, dict] = {}      # template -> 설명서 한 장
    edges: dict[str, set] = {}       # template -> 실제로 이동해 본 곳
    visited: set = set()             # (url, 요소이름) — 같은 것을 또 누르지 않도록
    steps: list[dict] = []
    shots_saved = 0
    dry = 0
    stop = "max_steps"

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=not args.headed)
        ctx = await browser.new_context(viewport=config.VIEWPORT)
        page = await ctx.new_page()
        await page.goto(root + "/index.html", timeout=config.STEP_TIMEOUT_MS)

        # 링크·디렉터리로 알 수 있는 목록은 '가봐야 할 곳' 힌트로만 쓴다.
        # 이 목록이 곧 정답은 아니다 — 눌러야 나오는 화면은 여기에 없다.
        known = await discover.discover(
            page, root,
            serve_root=None if args.no_local_dir else args.serve_root,
            max_pages=config.SURVEY_MAX_PAGES)
        # 템플릿 키는 절대 경로 기준(discover.template_key)이고 rel_path 는 root
        # 기준이다. 두 좌표계를 섞으면 이미 간 곳이 '못 간 곳'으로 찍힌다.
        todo_all = [{"key": discover.template_key(t["url"]),
                     "path": discover.rel_path(t["url"], root)}
                    for t in known["targets"]]
        await page.goto(root + "/index.html", timeout=config.STEP_TIMEOUT_MS)

        for n in range(1, args.max_steps + 1):
            if args.max_usd and usage.as_dict()["cost_usd"] >= args.max_usd:
                stop = "budget_stop"
                break

            snap = await take_snapshot(page)
            key = discover.template_key(snap["url"])
            is_new = key not in pages

            # 촬영과 '모델에 보내는 것'은 별개다. --mock 이어도 --shots-dir 를 주면
            # 찍어서 남긴다. 크레딧 없이도 촬영 경로가 도는지 눈으로 확인할 수 있어야 한다.
            shot = None
            if not args.mock or args.shots_dir:
                shot = await page.screenshot(type="png")
                shots_saved += 1
                if args.shots_dir:
                    os.makedirs(args.shots_dir, exist_ok=True)
                    name = "%02d_%s.png" % (n, discover.rel_path(page.url, root)
                                            .strip("/").split("?")[0] or "index")
                    with open(os.path.join(args.shots_dir, name), "wb") as f:
                        f.write(shot)

            todo = [t["path"] for t in todo_all if t["key"] not in pages]
            if args.mock:
                out = S.mock_decide(snap, set(pages), visited)
            else:
                try:
                    out = S.decide(client, models=model_list,
                                   snap_text=render_for_prompt(snap), shot=shot,
                                   recorded=sorted(pages), todo=todo,
                                   history=history_line(steps), usage=usage)
                except Exception as e:  # noqa: BLE001
                    # 40스텝을 달리다 한 번의 일시 장애(503)로 전부 잃으면 안 된다.
                    # 여기서 멈추되, 여태 모은 설명서는 아래에서 그대로 저장한다.
                    print("  [%2d] 모델 호출 실패 — 멈추고 여태 모은 것을 저장합니다." % n)
                    print("       %s" % " ".join(str(e).split())[:180])
                    stop = "llm_error"
                    break

            record, issues = S.clean_record(out.get("record"))
            if issues:
                # 판단 표현이 섞이면 그 기록만 버린다. 지도는 사실만 담아야 한다.
                print("      판단 표현 %d건 → 이 화면 기록은 버립니다: %s"
                      % (len(issues), issues[0]))
                record = None

            if is_new and record:
                pages[key] = S.page_entry(snap, record, root,
                                          "scout" if n > 1 else "link")
                dry = 0
                print("  [%2d] + %s  %s" % (n, pages[key]["path"], snap["title"][:30]))
            else:
                dry += 1

            action = out["action"]
            before_key = key
            if action["type"] == "done":
                stop = "done"
                steps.append({"n": n, "url": snap["url"], "title": snap["title"],
                              "thought": out["thought"], "action": action,
                              "recorded": bool(is_new and record),
                              "note": "더 볼 곳이 없다고 판단"})
                break

            if action.get("target"):
                visited.add((snap["url"], action["target"]))
            el = next((e for e in snap["elements"]
                       if e["id"] == action.get("target")), None)
            outcome = await explore.execute(page, action, root, el)
            steps.append({"n": n, "url": snap["url"], "title": snap["title"],
                          "thought": out["thought"], "action": action,
                          "recorded": bool(is_new and record),
                          "note": outcome.get("note", "")})

            after_key = discover.template_key(page.url)
            if after_key != before_key:
                edges.setdefault(before_key, set()).add(after_key)

            if not args.quiet:
                tgt = (" " + action["target"]) if action.get("target") else ""
                print("  [%2d] %s%s — %s" % (n, action["type"], tgt, out["thought"][:60]))

            # 맴돌면 다음 미기록 화면으로 강제 이동한다.
            # 답사자의 일은 '사람 흉내'가 아니라 '지도 완성'이라, 막혔을 때
            # 순간이동시키는 편이 낫다. 페르소나에게는 절대 허용하지 않는다.
            last3 = [(x["action"]["type"], x["action"].get("target"))
                     for x in steps[-3:]]
            if len(last3) == 3 and len(set(last3)) == 1:
                nxt = [t for t in todo_all if t["key"] not in pages]
                if nxt:
                    dest = root.rstrip("/") + nxt[0]["path"]
                    print("  [%2d] 같은 행동 3회 반복 → %s 로 건너뜁니다"
                          % (n, nxt[0]["path"]))
                    await page.goto(dest, timeout=config.STEP_TIMEOUT_MS)
                    steps.append({"n": n, "url": page.url, "title": snap["title"],
                                  "thought": "(막혀서 다음 화면으로 건너뜀)",
                                  "action": {"type": "goto", "target": nxt[0]["path"]},
                                  "recorded": False, "note": "맴돌이 탈출"})
                    continue
                stop = "loop"
                break

            if dry >= args.dry_rounds:
                stop = "dry"
                break

        await ctx.close()
        await browser.close()

    # 탐험 일기. 지도만 남기면 '어떻게 그 지도가 나왔는가'가 사라진다.
    # 답사가 어디서 막혔는지는 지도에 안 보이고 여기에만 보인다.
    os.makedirs("logs", exist_ok=True)
    diary_path = os.path.join(
        "logs", "scout_%s_%s.json" % (args.variant, datetime.now().strftime("%m%d_%H%M")))
    with open(diary_path, "w", encoding="utf-8") as f:
        json.dump({"kind": "scout", "variant": args.variant, "root": root,
                   "generated_at": datetime.now().isoformat(timespec="seconds"),
                   "stop_reason": stop, "mock": args.mock,
                   "screenshots": shots_saved, "pages_found": sorted(pages),
                   "steps": steps}, f, ensure_ascii=False, indent=1)
    print("탐험 일기: %s" % diary_path)

    if not pages:
        print("설명서가 비었습니다. 저장하지 않습니다.")
        return 2

    ordered = list(pages.values())
    for p in ordered:
        p["links_to"] = sorted(edges.get(p["template"], []))

    # 못 간 곳을 못 갔다고 말하는 것이 이 도구의 신뢰 논리다.
    unreached = [t["path"] for t in todo_all if t["key"] not in pages]

    site_map = {
        "variant": args.variant,
        "root": root,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "pages": ordered,
        "unreached": unreached,
        "structure": " → ".join(p["title"] for p in ordered),
    }

    issues = SV.validate_map(site_map)
    if issues:
        print("\n지도 전체 검사에서 %d건: %s" % (len(issues), issues[:5]))
        return 2

    print("\n" + "-" * 62)
    print("  종료: %s / %d스텝 / 화면 %d종" % (stop, len(steps), len(ordered)))
    for p in ordered:
        names = ", ".join(e.get("name", "?") for e in p["elements"][:6])
        print("   %-24s %s" % (p["path"], names[:60]))
    if unreached:
        print("  못 간 곳 %d: %s" % (len(unreached), ", ".join(unreached)))
    u = usage.as_dict()
    print("  이미지 %d장 / 호출 %d회 / 약 $%s" % (shots_saved, u["calls"], u["cost_usd"]))
    print("-" * 62)

    if not args.yes:
        ans = input("이 설명서를 저장할까요? [저장=엔터 / 중단=q] ").strip().lower()
        if ans == "q":
            print("저장하지 않았습니다.")
            return 1

    os.makedirs(config.MAPS_DIR, exist_ok=True)
    mp = os.path.join(config.MAPS_DIR, "site_map_%s.json" % args.variant)
    if os.path.exists(mp):
        # 기존 지도를 말없이 덮지 않는다. 정적 답사기 결과와 비교해야 한다.
        shutil.copyfile(mp, mp + ".bak")
        print("기존 지도를 %s.bak 으로 백업했습니다." % os.path.basename(mp))
    with open(mp, "w", encoding="utf-8") as f:
        json.dump(site_map, f, ensure_ascii=False, indent=2)

    meta = {
        "variant": args.variant,
        "generated_at": site_map["generated_at"],
        "surveyor": "scout",           # 정적 답사기(survey.py)와 구분하는 표시
        "provider": None if args.mock else pname,
        "model": None if args.mock else model,
        "model_fallbacks": [] if args.mock else model_list[1:],
        "mock": args.mock,
        "viewport": config.VIEWPORT,
        "steps": len(steps),
        "stop_reason": stop,
        "screenshots": shots_saved,
        "pages": len(ordered),
        "unreached": unreached,
        "usage": u,
    }
    mmp = os.path.join(config.MAPS_DIR, "survey_meta_%s.json" % args.variant)
    with open(mmp, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    print("저장: %s\n      %s" % (mp, mmp))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="답사 페르소나 — 조작하며 설명서 작성")
    ap.add_argument("--variant", default="clean", choices=sorted(config.SITE_DIRS))
    ap.add_argument("--base", default=config.DEFAULT_BASE)
    ap.add_argument("--serve-root", default=config.DEFAULT_SERVE_ROOT)
    ap.add_argument("--no-local-dir", action="store_true",
                    help="디렉터리 힌트를 끈다 (남의 사이트와 동일 조건)")
    ap.add_argument("--max-steps", type=int, default=40)
    ap.add_argument("--dry-rounds", type=int, default=15,
                    help="새 화면이 이만큼 연속으로 안 나오면 종료. "
                         "결제 폼 하나를 채우는 데만 6~10스텝이 든다 — "
                         "너무 낮게 잡으면 폼 앞에서 답사가 끝난다")
    ap.add_argument("--shots-dir", default="",
                    help="스크린샷을 남길 폴더 (발표용). 비우면 저장하지 않는다")
    ap.add_argument("--max-usd", type=float, default=1.0)
    ap.add_argument("--headed", action="store_true")
    ap.add_argument("--mock", action="store_true")
    ap.add_argument("--quiet", action="store_true")
    ap.add_argument("--yes", action="store_true")
    args = ap.parse_args()
    args.max_usd = args.max_usd or None
    return asyncio.run(run(args))


if __name__ == "__main__":
    raise SystemExit(main())
