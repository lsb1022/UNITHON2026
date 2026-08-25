"""페르소나 생성기 CLI — 목표 하나로 100명을 조립한다.

    python generate.py --goal "코튼 셔츠를 장바구니에 담아 주문까지 마친다"
    python generate.py --goal "..." --start /list.html --n 20
    python generate.py --validate-only
    python generate.py --auto-goals            # 옛 방식(목표 11개 자동 생성). 기본 꺼짐

목표와 시작 지점은 **전원 동일**하고 파일 상단에 한 번만 저장한다.
100명에게 복사하면 파일이 커지고, 목표를 고칠 때 100군데를 고쳐야 한다.

목표 문자열에도 답사자에게 걸었던 **금칙어 필터를 건다.**
"결제 버튼이 작동하는지 확인" 같은 입력이 들어오면 100명 전원이 그 결함을
찾으러 가는데, 그건 우리가 미리 답을 알려준 것이라 적중률이 무의미해진다.

옛 방식(지도를 보고 목표 11개를 자동 생성)은 `uxagent/goals.py` 에 그대로
남아 있다. 지우지 않았다 — 목표를 여러 개로 다시 돌릴 때 필요하다.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import Counter
from datetime import datetime

# Windows 콘솔 기본 코드페이지(cp949)에서 한글이 깨진다. 출력만 UTF-8로 고정.
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:  # noqa: BLE001 - 리다이렉트된 스트림이면 무시
        pass

from uxagent import config, persona as P
from uxagent import survey as SV

# 낱말 단위로 지도와 대조할 때 쓴다. 조사·어미를 떼지 않는 단순 비교이므로
# '경고'로만 쓰고 실행을 막지는 않는다.
_WORD = re.compile(r"[가-힣]{2,}")
# 지도에 없어도 정상인 일반 동작 낱말. 이런 것까지 경고하면 잡음만 늘어난다.
_COMMON = {
    "장바구니", "담기", "담아", "주문", "결제", "구매", "상품", "확인", "선택",
    "이동", "검색", "화면", "페이지", "가격", "수량", "사이즈", "색상", "배송",
    "마친다", "한다", "본다", "찾는다", "고른다", "넣는다", "까지", "그리고",
    "하나", "두개", "모두", "다시", "이내", "미만", "이상",
}


def clean_path(path: str) -> str:
    """Git Bash 는 "/index.html" 같은 인자를 윈도우 경로로 바꿔버린다
    ("C:/Program Files/Git/index.html"). 그대로 저장하면 100명 전원이
    존재하지 않는 주소에서 시작해 요소 0개를 보고 즉시 맴돈다.
    실제로 겪었다 — 지도에 없는 화면 9회로 나타났다."""
    p = (path or "").strip()
    if ":" in p and "/" in p:
        p = "/" + p.rsplit("/", 1)[-1]
    return "/" + p.lstrip("/")


def load_map(variant: str) -> dict:
    path = os.path.join(config.MAPS_DIR, "site_map_%s.json" % variant)
    if not os.path.exists(path):
        raise SystemExit("지도가 없습니다: %s\n  먼저: python scout.py --variant %s"
                         % (path, variant))
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def map_vocabulary(site_map: dict) -> set:
    """지도에 실제로 등장하는 낱말. 목표가 없는 기능을 요구하는지 볼 때 쓴다."""
    blob = []
    for p in site_map.get("pages", []):
        blob += [str(p.get("title") or ""), str(p.get("layout") or ""), p["path"]]
        for e in p.get("elements") or []:
            blob += [str(e.get("name") or ""), str(e.get("where") or "")]
    return set(_WORD.findall(" ".join(blob)))


def check_goal(goal: str, site_map: dict) -> tuple[list[str], list[str]]:
    """(막아야 할 문제, 경고) 를 돌려준다."""
    errors, warns = [], []
    g = (goal or "").strip()
    if not g:
        return ["목표가 비었습니다"], warns
    if len(g) > 60:
        errors.append("목표가 %d자입니다. 60자 이내로 줄이세요 "
                      "(프롬프트 상한 %d자를 지켜야 합니다)"
                      % (len(g), config.PROMPT_MAX_CHARS))
    for w in SV._scan(g):
        errors.append("판단 표현 '%s' — 목표는 '할 일'이지 '결함'이 아닙니다. "
                      "이대로 넣으면 100명 전원이 그 결함을 찾으러 갑니다" % w)
    for msg in SV._lang_issues(g):
        errors.append("목표: %s" % msg)

    # 지도에 없는 기능을 요구하는지. 확실히 판정할 수 없으므로 경고만 한다.
    unknown = [w for w in _WORD.findall(g)
               if w not in map_vocabulary(site_map) and w not in _COMMON]
    if unknown:
        warns.append("지도에서 확인되지 않은 낱말: %s — 그런 기능이 사이트에 없으면 "
                     "전원이 실패해 리포트가 무의미해집니다" % ", ".join(unknown[:6]))
    return errors, warns


def print_summary(goal: str, start: str, people: list[dict]) -> None:
    print("\n" + "=" * 62)
    print("  목표: %s" % goal)
    print("  시작: %s   인원: %d명" % (start, len(people)))
    print("=" * 62)

    combos = {tuple(p["traits"][a] for a in P.AXES) for p in people}
    print("고유 조합 %d / %d명" % (len(combos), len(people)))
    for a in P.AXES:
        c = Counter(p["traits"][a] for p in people)
        print("  %-6s %s" % (P.AXIS_LABEL[a],
                             "  ".join("%d단계 %2d명" % (k, c[k]) for k in sorted(c))))

    dwell10 = sum(1 for p in people if p["dwell_ms"] >= 10000)
    print("\n체류 10초 이상: %d명" % dwell10)
    print("  ↳ 자동 팝업은 로드 10초 후에 뜬다. 이 인원이 0이면 그 결함은")
    print("    아무도 마주치지 못하고, 못 잡은 게 아니라 만난 적이 없는 것이 된다.")
    print("주소창 입력 허용: %d명 (숙련도 3 이상)"
          % sum(1 for p in people if P.URL_ACTION in p["allowed_actions"]))
    print("방문 화면 %d종 제한: %d명 (탐색 범위 2 이하)"
          % (P.NARROW_PAGE_CAP, sum(1 for p in people if p["page_cap"])))
    print("최장 프롬프트: %d자 (상한 %d자)"
          % (max(len(p["prompt"]) for p in people), config.PROMPT_MAX_CHARS))

    print("-" * 62)
    x = people[0]
    print("예시 — %s  %s" % (x["id"], x["label"]))
    for line in x["prompt"].splitlines():
        print("   | %s" % line)
    print("   | 체류 %dms / 최대 %d스텝 / 헛시도 %d회까지 / 행동 %s"
          % (x["dwell_ms"], x["max_steps"], x["max_idle_attempts"],
             ",".join(x["allowed_actions"])))
    print("-" * 62)


def save(goal: str, start: str, people: list[dict], site_map: dict,
         variant: str) -> tuple[str, str]:
    os.makedirs(config.PERSONAS_DIR, exist_ok=True)
    pp = os.path.join(config.PERSONAS_DIR, "personas.json")
    payload = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        # 목표와 시작 지점은 여기 한 번만. 사람마다 복사하지 않는다.
        "goal": goal,
        "start_path": start,
        "seed": config.PERSONA_SEED,
        "axes": {a: P.AXIS_LABEL[a] for a in P.AXES},
        "source_map": {"variant": variant, "generated_at": site_map.get("generated_at")},
        "personas": people,
    }
    with open(pp, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=1)

    meta = {
        "generated_at": payload["generated_at"],
        "goal": goal,
        "start_path": start,
        "counts": {
            "personas": len(people),
            "unique_combos": len({tuple(p["traits"][a] for a in P.AXES) for p in people}),
            "dwell_over_10s": sum(1 for p in people if p["dwell_ms"] >= 10000),
            "url_allowed": sum(1 for p in people if P.URL_ACTION in p["allowed_actions"]),
            "page_capped": sum(1 for p in people if p["page_cap"]),
            "by_axis": {a: dict(sorted(Counter(p["traits"][a] for p in people).items()))
                        for a in P.AXES},
        },
    }
    mp = os.path.join(config.PERSONAS_DIR, "personas_meta.json")
    with open(mp, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    return pp, mp


def validate_only() -> int:
    pp = os.path.join(config.PERSONAS_DIR, "personas.json")
    if not os.path.exists(pp):
        print("파일이 없습니다: %s" % pp)
        return 2
    with open(pp, encoding="utf-8") as f:
        data = json.load(f)
    people = data["personas"]
    issues = []

    combos = {tuple(p["traits"][a] for a in P.AXES) for p in people}
    if len(combos) != len(people):
        issues.append("조합 중복 %d건" % (len(people) - len(combos)))
    for a in P.AXES:
        c = Counter(p["traits"][a] for p in people)
        if max(c.values()) - min(c.values()) > 1:
            issues.append("%s 분포가 고르지 않습니다: %s" % (P.AXIS_LABEL[a], dict(c)))
    for p in people:
        if len(p["prompt"]) > config.PROMPT_MAX_CHARS:
            issues.append("%s 프롬프트 %d자" % (p["id"], len(p["prompt"])))
        if p["traits"]["literacy"] <= 2 and P.URL_ACTION in p["allowed_actions"]:
            issues.append("%s 숙련도 %d인데 주소창이 허용됨"
                          % (p["id"], p["traits"]["literacy"]))
    if not any(p["dwell_ms"] >= 10000 for p in people):
        issues.append("체류 10초 이상인 사람이 없습니다 — 시간 의존 결함을 아무도 못 만납니다")

    if issues:
        print("%d건:" % len(issues))
        for it in issues:
            print("   - %s" % it)
        return 2
    print("%s: %d명 / 고유 조합 %d / 목표 \"%s\" — 이상 없음."
          % (pp, len(people), len(combos), data.get("goal")))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="페르소나 생성기 — 특성 4축 x 1~5단계")
    ap.add_argument("--goal", default="", help="전원이 공유할 목표 한 문장")
    ap.add_argument("--start", default="/index.html", help="전원 동일한 시작 화면")
    ap.add_argument("--variant", default="clean", choices=sorted(config.SITE_DIRS),
                    help="목표를 대조할 지도. 기본 clean")
    ap.add_argument("--n", type=int, default=config.N_PERSONAS)
    ap.add_argument("--yes", action="store_true", help="사람 확인 단계 생략")
    ap.add_argument("--validate-only", action="store_true")
    ap.add_argument("--auto-goals", action="store_true",
                    help="옛 방식: 지도를 보고 목표 11개를 자동 생성. 지금은 쓰지 않음")
    args = ap.parse_args()

    if args.validate_only:
        return validate_only()
    if args.auto_goals:
        print("옛 방식(목표 11개 자동 생성)은 uxagent/goals.py 에 그대로 남아 있지만")
        print("지금 설계에서는 쓰지 않습니다. --goal 로 목표 하나를 주세요.")
        return 2
    if not args.goal:
        print("목표가 필요합니다:  python generate.py --goal \"...\"")
        return 2

    site_map = load_map(args.variant)
    errors, warns = check_goal(args.goal, site_map)
    for w in warns:
        print("경고: %s" % w)
    if errors:
        print("\n목표를 그대로 쓸 수 없습니다:")
        for e in errors:
            print("   - %s" % e)
        return 2
    if warns and not args.yes:
        ans = input("\n경고가 있습니다. 계속할까요? [계속=엔터 / 중단=q] ").strip().lower()
        if ans == "q":
            return 1

    start = clean_path(args.start)
    if start != args.start:
        print("시작 경로를 %r 로 바로잡았습니다 (셸이 %r 로 바꿔놨습니다)"
              % (start, args.start))
    people = P.build(args.goal.strip(), start, n=args.n)
    print_summary(args.goal.strip(), start, people)

    if not args.yes:
        ans = input("\n이대로 %d명을 저장할까요? [저장=엔터 / 중단=q] "
                    % len(people)).strip().lower()
        if ans == "q":
            print("저장하지 않았습니다.")
            return 1

    pp, mp = save(args.goal.strip(), start, people, site_map, args.variant)
    print("\n저장: %s\n      %s" % (pp, mp))
    print("\n목표와 시작 지점은 파일 상단에 한 번만 있습니다. "
          "사람마다 다른 것은 특성과 거기서 나온 제약뿐입니다.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
