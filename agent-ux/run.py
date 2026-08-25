"""페르소나 실행기 CLI — 사람이 사이트를 돌아다니게 하고 전부 기록한다.

    python run.py --variant buggy                      # 기본: 한 명만
    python run.py --variant buggy --headed             # 창을 띄우고 한 명
    python run.py --variant buggy --limit 3            # 세 명
    python run.py --variant buggy --all                # 100명 (비용 확인 후)
    python run.py --variant buggy --mock               # LLM 없이 루프만

**기본값이 한 명인 이유**: 스텝마다 LLM을 부른다. 100명 × 평균 25스텝이면
한 번 실행에 2,500회다. 실수로 전부 도는 일이 없도록 100명은 `--all` 을
명시해야만 돌고, 그때도 예상 호출 수를 먼저 보여준다.

`--max-usd` 를 넘으면 그 자리에서 멈추고, 그 사람의 종료 사유는
`budget_stop` 으로 남는다. 우리가 끊은 것을 '포기'로 적으면 마찰 지점
통계가 오염되기 때문이다.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
from datetime import datetime

# Windows 콘솔 기본 코드페이지(cp949)에서 한글이 깨진다. 출력만 UTF-8로 고정.
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:  # noqa: BLE001 - 리다이렉트된 스트림이면 무시
        pass

from uxagent import config, explore, persona as P, trace as T
from uxagent.llm import Usage, build_client
from uxagent.snapshot import take_snapshot
from uxagent.survey import get_map_slice


class Budget:
    """예산 감시. 넘으면 실행을 멈춘다.

    크레딧이 빠듯한 상태에서 100명을 잘못 돌리면 되돌릴 수 없다.
    상한을 넘겼는지 확인하는 것은 사람이 아니라 코드의 일이다.
    """

    def __init__(self, usage: Usage, max_usd: float | None, max_calls: int | None):
        self.usage = usage
        self.max_usd = max_usd
        self.max_calls = max_calls
        self.stopped = ""

    def spent(self) -> float:
        return self.usage.as_dict()["cost_usd"]

    def exceeded(self) -> str:
        if self.max_calls and self.usage.calls >= self.max_calls:
            return "호출 %d회 상한 도달" % self.max_calls
        if self.max_usd and self.spent() >= self.max_usd:
            return "$%.4f (상한 $%.2f) 도달" % (self.spent(), self.max_usd)
        return ""


async def run_persona(browser, person: dict, site_map: dict | None, root: str,
                      *, client, model: str, usage: Usage, budget: Budget,
                      mock: bool, run_id: str, variant: str, use_map: bool,
                      quiet: bool) -> dict:
    """한 명을 끝까지 돌리고 즉시 저장한다.

    페르소나마다 컨텍스트를 새로 연다. 쿠키와 localStorage 가 섞이면
    '처음 온 사람'이 앞사람의 장바구니를 물려받는다.
    """
    ctx = await browser.new_context(viewport=config.VIEWPORT)
    page = await ctx.new_page()
    tr = T.Trace(run_id, person, variant)
    end_reason, note = "max_steps", ""
    seeded = 0

    try:
        start = root.rstrip("/") + "/" + person["start_path"].lstrip("/")
        await page.goto(start, timeout=config.STEP_TIMEOUT_MS)

        # 장바구니 시딩. 키는 여기서 붙인다 — 페르소나 파일에는 키가 없다.
        # 같은 파일을 clean/buggy 양쪽에 넣기 때문이다.
        if person.get("seed_state"):
            seeded = await page.evaluate(
                P.seed_script(person["seed_state"], config.cart_key(variant)))
            tr.extra["seeded_lines"] = seeded
            await page.reload(timeout=config.STEP_TIMEOUT_MS)

        seen_url = None
        for n in range(1, person["max_steps"] + 1):
            if budget.exceeded():
                end_reason, note = "budget_stop", budget.exceeded()
                break

            # 새 화면에 도착했으면 그 사람의 성격만큼 머문다.
            # D-26(자동 팝업)은 로드 10초 후에 뜬다. 훑고 지나가는 사람은
            # 그 결함을 만나지 못하고, 그건 '못 잡은 것'이 아니라
            # '마주친 적이 없는 것'이다. 이 차이가 기록에 남아야 한다.
            if page.url != seen_url:
                seen_url = page.url
                await asyncio.sleep(person["dwell_ms"] / 1000)

            t0 = time.monotonic()
            snap = await take_snapshot(page)

            slice_ = get_map_slice(site_map, page.url, root) if use_map else None
            map_miss = bool(use_map and slice_ is None)

            out = explore.decide(client, person, snap, tr.steps, slice_,
                                 model=model, usage=usage, mock=mock)
            action, thought = out["action"], out["thought"]

            blocked = explore.check_allowed(action, person)
            if blocked:
                outcome = {"changed": False, "url_after": page.url,
                           "note": "허용되지 않은 행동이라 하지 않았습니다"}
            elif action["type"] == "done":
                outcome = {"changed": False, "url_after": page.url, "note": "목표를 이뤘다고 판단"}
            elif action["type"] == "give_up":
                outcome = {"changed": False, "url_after": page.url, "note": "포기"}
            else:
                el = next((e for e in snap["elements"]
                           if e["id"] == action.get("target")), None)
                outcome = await explore.execute(page, action, root, el)

            tr.add(T.step(
                n, thought=thought, action=action, snapshot=T.slim(snap),
                resolved=T.resolve(snap, action.get("target")),
                outcome=outcome, map_slice_used=slice_ is not None,
                map_miss=map_miss, blocked_action=blocked,
                elapsed_ms=int((time.monotonic() - t0) * 1000)))

            if not quiet:
                tgt = (" " + action["target"]) if action.get("target") else ""
                print("  [%s] %2d/%d  %s%s%s\n        %s"
                      % (person["id"], n, person["max_steps"], action["type"], tgt,
                         "  ⨯차단" if blocked else "", thought[:70]), flush=True)

            if action["type"] == "done":
                end_reason = "goal_reached"
                break
            if action["type"] == "give_up":
                end_reason = "gave_up"
                break
            if explore.loop_detected(tr.steps, page.url):
                end_reason = "loop_detected"
                break

    except Exception as e:  # noqa: BLE001 - 한 명이 죽어도 나머지는 돌아야 한다
        end_reason, note = "error", explore._short_error(e)
    finally:
        await ctx.close()

    path = tr.finish(end_reason, note)
    d = tr.as_dict(note)
    print("  [%s] %s — %d스텝  (%s)" % (person["id"], end_reason, len(tr.steps), path))
    return d


async def main_async(args) -> int:
    from playwright.async_api import async_playwright

    pf = os.path.join(config.PERSONAS_DIR, "personas.json")
    if not os.path.exists(pf):
        raise SystemExit("페르소나 파일이 없습니다: %s\n  먼저: python generate.py --mock --yes" % pf)
    with open(pf, encoding="utf-8") as f:
        data = json.load(f)
    people = data["personas"]

    if args.only:
        people = [p for p in people if p["id"] in set(args.only)]
        if not people:
            raise SystemExit("그런 페르소나가 없습니다: %s" % ", ".join(args.only))
    elif args.all:
        pass
    else:
        people = people[:args.limit]

    root = config.site_root(args.variant, args.base)
    use_map = not args.no_map
    site_map = None
    if use_map:
        mp = os.path.join(config.MAPS_DIR, "site_map_%s.json" % args.variant)
        if not os.path.exists(mp):
            raise SystemExit("지도가 없습니다: %s\n  먼저: python survey.py --variant %s"
                             % (mp, args.variant))
        with open(mp, encoding="utf-8") as f:
            site_map = json.load(f)

    usage = Usage()
    budget = Budget(usage, args.max_usd, args.max_calls)
    pname = config.role_provider("explore")
    client = None if args.mock else build_client(pname)
    model = config.model("explore", pname)
    run_id = args.run_id or "%s_%s%s" % (
        datetime.now().strftime("%m%d_%H%M"), args.variant, "" if use_map else "_nomap")

    steps_est = sum(p["max_steps"] for p in people)
    print("=" * 62)
    print("  실행 %s   대상 %s   지도 %s%s"
          % (run_id, args.variant, "사용" if use_map else "없음", "   [모의]" if args.mock else ""))
    print("  페르소나 %d명 / 최대 %d스텝 = LLM 호출 최대 %d회"
          % (len(people), steps_est, 0 if args.mock else steps_est))
    if not args.mock:
        print("  %s / %s   상한 $%s / %s회"
              % (pname, model, args.max_usd, args.max_calls or "무제한"))
    print("=" * 62)

    # 100명은 실수로 돌아가면 안 된다. 크레딧은 되돌릴 수 없다.
    if args.all and not args.mock and not args.yes:
        ans = input("100명을 전부 돌립니다. 계속할까요? [진행=엔터 / 중단=q] ").strip().lower()
        if ans == "q":
            print("중단했습니다.")
            return 1

    traces = []
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=not args.headed)
        sem = asyncio.Semaphore(args.parallel)

        async def one(person):
            async with sem:
                if budget.exceeded():
                    return None
                return await run_persona(
                    browser, person, site_map, root, client=client, model=model,
                    usage=usage, budget=budget, mock=args.mock, run_id=run_id,
                    variant=args.variant, use_map=use_map, quiet=args.quiet)

        results = await asyncio.gather(*(one(p) for p in people))
        traces = [t for t in results if t]
        await browser.close()

    u = usage.as_dict()
    idx = T.write_index(run_id, args.variant, traces, extra={
        "variant": args.variant, "map_used": use_map, "mock": args.mock,
        "provider": None if args.mock else pname,
        "model": None if args.mock else model,
        "usage": u,
        "source_personas": data.get("generated_at"),
    })

    print("\n" + "-" * 62)
    ends = {}
    for t in traces:
        ends[t["end_reason"]] = ends.get(t["end_reason"], 0) + 1
    for k in T.END_REASONS:
        if ends.get(k):
            print("  %-14s %d명" % (k, ends[k]))
    misses = sum(1 for t in traces for s in t["steps"] if s["map_miss"])
    blocked = sum(1 for t in traces for s in t["steps"] if s["blocked_action"])
    print("  지도에 없던 화면 %d회 / 허용 밖 행동 %d회" % (misses, blocked))
    print("  호출 %d회 / 입력 %d · 출력 %d 토큰 / 약 $%s"
          % (u["calls"], u["tokens_in"], u["tokens_out"], u["cost_usd"]))
    if budget.exceeded():
        print("  ⚠ 예산 상한에서 멈췄습니다: %s" % budget.exceeded())
    print("  목록: %s" % idx)
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="페르소나 실행기 — 탐색 루프")
    ap.add_argument("--variant", default="buggy", choices=sorted(config.SITE_DIRS))
    ap.add_argument("--base", default=config.DEFAULT_BASE)
    ap.add_argument("--only", action="append", default=[],
                    help="특정 페르소나만 (예: --only P001). 반복 지정 가능")
    ap.add_argument("--limit", type=int, default=1,
                    help="앞에서 N명. 기본 1명 — 토큰을 아끼기 위한 기본값이다")
    ap.add_argument("--all", action="store_true", help="100명 전부 (확인을 한 번 더 묻는다)")
    ap.add_argument("--no-map", action="store_true", help="지도 없이 (A/B 검증용)")
    ap.add_argument("--headed", action="store_true", help="브라우저 창을 띄운다")
    ap.add_argument("--mock", action="store_true", help="LLM 없이 루프만 확인")
    ap.add_argument("--parallel", type=int, default=1,
                    help="동시 실행 수. 기본 1 (창을 띄울 때는 1이 낫다)")
    ap.add_argument("--max-usd", type=float, default=1.0,
                    help="이 금액을 넘으면 멈춘다. 0이면 무제한")
    ap.add_argument("--max-calls", type=int, default=0,
                    help="이 호출 수를 넘으면 멈춘다. 0이면 무제한")
    ap.add_argument("--run-id", default="")
    ap.add_argument("--quiet", action="store_true", help="스텝별 출력을 끈다")
    ap.add_argument("--yes", action="store_true", help="--all 확인 생략")
    args = ap.parse_args()
    args.max_usd = args.max_usd or None
    args.max_calls = args.max_calls or None
    return asyncio.run(main_async(args))


if __name__ == "__main__":
    raise SystemExit(main())
