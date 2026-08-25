"""페르소나 생성기 CLI — 목표 11개를 만들고 100명을 조립해 저장한다.

    python generate.py --mock --yes      # LLM 없이 (기본 목표 사용)
    python generate.py                   # 지도를 보고 LLM이 목표 생성
    python generate.py --validate-only   # 저장된 파일 재검사

지도는 **clean 기준**으로 읽는다 (결정 6). flawed 를 보고 목표를 만들면
깨진 링크와 사라진 요소가 목표 자체를 오염시켜, 애초에 불가능한 일을
시켜놓고 '실패율'을 재게 된다. 만들어진 personas.json 은 clean/buggy
양쪽에 동일하게 투입한다.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter
from datetime import datetime

# Windows 콘솔 기본 코드페이지(cp949)에서 한글이 깨진다. 출력만 UTF-8로 고정.
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:  # noqa: BLE001 - 리다이렉트된 스트림이면 무시
        pass

from uxagent import config, goals as G, persona as P
from uxagent.llm import Usage, build_client

TYPE_LABEL = {"A": "구매 완수", "B": "정보 확인", "C": "중단·재개"}


def load_map(variant: str) -> dict:
    path = os.path.join(config.MAPS_DIR, "site_map_%s.json" % variant)
    if not os.path.exists(path):
        raise SystemExit("지도가 없습니다: %s\n  먼저: python survey.py --variant %s"
                         % (path, variant))
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def check_pairs(people: list[dict]) -> tuple[int, int]:
    """(조합, 목표) 쌍이 몇 개나 겹치는지. 0이어야 한다."""
    pairs = [(p["combo_index"], p["goal_id"]) for p in people]
    return len(set(pairs)), len(pairs) - len(set(pairs))


def print_summary(goals: list[dict], people: list[dict]) -> None:
    print("\n" + "=" * 62)
    print("  목표 %d개 x 조합 %d개 -> 페르소나 %d명"
          % (len(goals), len(P.combos()), len(people)))
    print("=" * 62)

    for g in goals:
        seed = " [장바구니 시딩]" if g.get("seed_state") else ""
        print("\n[%s·%s] %s" % (g["id"], TYPE_LABEL[g["type"]], g["text"]))
        print("   시작: %s%s" % (g["start_path"], seed))
        print("   성공: %s" % g.get("success", "-"))

    uniq, dup = check_pairs(people)
    seeded = sum(1 for p in people if p["seed_state"])
    dwell10 = sum(1 for p in people if p["dwell_ms"] >= 10000)
    goto = sum(1 for p in people if "goto" in p["allowed_actions"])
    longest = max(people, key=lambda p: len(p["prompt"]))

    print("\n" + "-" * 62)
    print("(조합, 목표) 쌍: 고유 %d / 중복 %d" % (uniq, dup))
    print("장바구니 시딩: %d명   URL 직접입력 허용: %d명" % (seeded, goto))
    print("한 페이지에 10초 이상 머무는 인원: %d명" % dwell10)
    print("  ↳ D-26(자동 팝업)은 로드 10초 후에 뜬다. 이 인원이 0이면 그 결함은")
    print("    아무도 만나지 못하고, 못 잡은 게 아니라 마주친 적이 없는 것이 된다.")
    print("최장 프롬프트: %d자 (상한 %d자)" % (len(longest["prompt"]), config.PROMPT_MAX_CHARS))
    print("-" * 62)
    print("예시 — %s  %s" % (people[0]["id"], people[0]["label"]))
    for line in people[0]["prompt"].splitlines():
        print("   | %s" % line)
    print("   | 허용 행동: %s / 최대 %d스텝 / 체류 %dms"
          % (",".join(people[0]["allowed_actions"]), people[0]["max_steps"],
             people[0]["dwell_ms"]))
    print("-" * 62)


def build_all(args) -> tuple[list[dict], list[dict], dict, Usage]:
    site_map = load_map(args.variant)
    paths = {p["path"] for p in site_map["pages"]}
    usage = Usage()
    pname = config.role_provider("goals")
    client = None if args.mock else build_client(pname)
    model = config.model("goals", pname)

    if not args.mock:
        print("프로바이더: %s / 모델: %s" % (pname, model))
    print("지도: %s (페이지 %d종)" % (args.variant, len(paths)))

    goals = G.generate(client, site_map, model=model, usage=usage, mock=args.mock)
    # 판단 표현·없는 경로·유형 분포를 코드가 검사한다. 통과할 때까지 재생성.
    for attempt in range(1, config.SURVEY_VALIDATE_RETRIES + 1):
        issues = G.validate(goals, paths)
        if not issues:
            break
        print("목표 검사 %d건 -> 재생성 %d회차" % (len(issues), attempt))
        for it in issues[:5]:
            print("   - %s" % it)
        if args.mock:
            # 기본 목록이 검사를 통과하지 못하면 재생성해도 같은 것이 나온다.
            raise SystemExit("기본 목표가 검사를 통과하지 못했습니다. goals.py를 고쳐야 합니다.")
        goals = G.generate(client, site_map, model=model, usage=usage, mock=False)
    else:
        issues = G.validate(goals, paths)
        if issues:
            print("\n%d회 재생성에도 %d건이 남았습니다:"
                  % (config.SURVEY_VALIDATE_RETRIES, len(issues)))
            for it in issues:
                print("   - %s" % it)
            raise SystemExit("저장하지 않고 중단합니다. 프롬프트를 손봐야 합니다.")

    goals = G.attach_seeds(goals)
    people = P.build(goals, n=args.n)
    return goals, people, site_map, usage


def validate_only(variant: str) -> int:
    pp = os.path.join(config.PERSONAS_DIR, "personas.json")
    if not os.path.exists(pp):
        print("파일이 없습니다: %s" % pp)
        return 2
    with open(pp, encoding="utf-8") as f:
        data = json.load(f)
    site_map = load_map(data.get("source_map", {}).get("variant", variant))
    paths = {p["path"] for p in site_map["pages"]}

    issues = G.validate(data["goals"], paths)
    people = data["personas"]
    uniq, dup = check_pairs(people)
    if dup:
        issues.append("(조합, 목표) 쌍 중복 %d건" % dup)
    for p in people:
        if len(p["prompt"]) > config.PROMPT_MAX_CHARS:
            issues.append("%s: 프롬프트 %d자" % (p["id"], len(p["prompt"])))
        if p["seed_state"] and p["user_type"] != "returning":
            issues.append("%s: 시딩됐는데 user_type 이 %s" % (p["id"], p["user_type"]))
    if issues:
        print("%d건:" % len(issues))
        for it in issues:
            print("   - %s" % it)
        return 2
    print("%s: 목표 %d개 / 페르소나 %d명 / 고유 쌍 %d — 이상 없음."
          % (pp, len(data["goals"]), len(people), uniq))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="페르소나 생성기 — 목표 11개 x 조합 16개")
    ap.add_argument("--variant", default="clean", choices=sorted(config.SITE_DIRS),
                    help="목표를 뽑을 지도. 기본 clean (결정 6)")
    ap.add_argument("--n", type=int, default=config.N_PERSONAS)
    ap.add_argument("--mock", action="store_true", help="LLM 없이 기본 목표 사용")
    ap.add_argument("--yes", action="store_true", help="사람 확인 단계 생략")
    ap.add_argument("--validate-only", action="store_true",
                    help="저장된 personas.json 재검사")
    args = ap.parse_args()

    if args.validate_only:
        return validate_only(args.variant)

    if args.variant != "clean":
        print("경고: clean 이 아닌 지도로 목표를 만들고 있습니다. "
              "깨진 링크가 목표를 오염시킬 수 있습니다 (결정 6).")

    goals, people, site_map, usage = build_all(args)
    print_summary(goals, people)

    uniq, dup = check_pairs(people)
    if dup:
        print("\n(조합, 목표) 쌍이 %d건 겹칩니다. 목표 개수를 16과 서로소로 두세요." % dup)
        return 2

    if not args.yes:
        ans = input("\n이 목표들로 %d명을 저장할까요? [저장=엔터 / 중단=q] "
                    % len(people)).strip().lower()
        if ans == "q":
            print("저장하지 않고 중단했습니다.")
            return 1

    os.makedirs(config.PERSONAS_DIR, exist_ok=True)
    pp = os.path.join(config.PERSONAS_DIR, "personas.json")
    payload = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "source_map": {"variant": args.variant,
                       "generated_at": site_map.get("generated_at")},
        "goals": goals,
        "personas": people,
    }
    with open(pp, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=1)

    meta = {
        "generated_at": payload["generated_at"],
        "provider": None if args.mock else config.role_provider("goals"),
        "model": None if args.mock else config.model("goals",
                                                     config.role_provider("goals")),
        "mock": args.mock,
        "counts": {
            "goals": len(goals),
            "combos": len(P.combos()),
            "personas": len(people),
            "unique_pairs": uniq,
            "seeded": sum(1 for p in people if p["seed_state"]),
            "dwell_over_10s": sum(1 for p in people if p["dwell_ms"] >= 10000),
            "goal_types": dict(Counter(g["type"] for g in goals)),
        },
        "usage": usage.as_dict(),
    }
    mp = os.path.join(config.PERSONAS_DIR, "personas_meta.json")
    with open(mp, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    u = meta["usage"]
    print("\n저장: %s" % pp)
    print("      %s" % mp)
    print("호출 %d회 / 입력 %d · 출력 %d 토큰 / 약 $%s"
          % (u["calls"], u["tokens_in"], u["tokens_out"], u["cost_usd"]))
    print("\n이 파일 하나를 clean/buggy 양쪽에 그대로 투입합니다. 장바구니 키는")
    print("변형마다 다르므로 러너가 config.cart_key(variant) 로 붙입니다.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
