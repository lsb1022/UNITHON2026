"""확인 화면의 '예상 소요 / 예상 사용량'.

실측이 없으므로 공식으로 낸다:

    소요(분)   = 페르소나 수 × 페이지 수 × MINUTES_WEIGHT
    토큰       = 페르소나 수 × 페이지 수 × TOKENS_WEIGHT

가중치는 디자인 시안의 기준값(100명 × 6페이지 → 약 6분 / 약 1.8M 토큰)에서 역산했다.
4회 본실행 뒤 실측이 나오면 이 상수 두 개만 갈아끼우면 된다.

기획서 7장이 못박은 주의사항을 그대로 지킨다:
    "'60분 → 30분'은 아직 실측이 없으므로 4회 실행 뒤에 쓸 것.
     단가표도 아직 콘솔 확인 전 추정치다."
그래서 결과에 measured=False 를 같이 실어 보낸다. 화면은 추정치를 실측처럼 보이면 안 된다.
"""

from __future__ import annotations

from dataclasses import dataclass

#: 답사로 확인된 화면 수를 모를 때 쓰는 기본값 (테스트베드 쇼핑몰이 6화면)
DEFAULT_PAGE_COUNT = 6

#: 분 / (페르소나 1명 × 페이지 1장). 100 × 6 × 0.01 = 6분
MINUTES_WEIGHT = 0.01

#: 토큰 / (페르소나 1명 × 페이지 1장). 100 × 6 × 3000 = 1.8M
TOKENS_WEIGHT = 3_000

#: 기획서 7장 — 1명당 최대 30스텝
MAX_STEPS_PER_PERSONA = 30

#: 실측 전이다. 콘솔 확인 후 교체할 것.
USD_PER_1K_TOKENS_ESTIMATE = 0.003


@dataclass
class RunEstimate:
    persona_count: int
    page_count: int
    max_text_calls: int
    vision_calls: int
    tokens: int
    minutes: int
    usd: float
    measured: bool
    formula: str


def estimate(persona_count: int, page_count: int = DEFAULT_PAGE_COUNT) -> RunEstimate:
    pages = max(1, page_count)
    tokens = persona_count * pages * TOKENS_WEIGHT

    return RunEstimate(
        persona_count=persona_count,
        page_count=pages,
        max_text_calls=persona_count * MAX_STEPS_PER_PERSONA,
        # 기획서 7장의 핵심: 답사 한 번만 이미지를 쓰고 뒤따르는 100명은 0회다.
        vision_calls=0,
        tokens=tokens,
        minutes=max(1, round(persona_count * pages * MINUTES_WEIGHT)),
        usd=round(tokens / 1000 * USD_PER_1K_TOKENS_ESTIMATE, 2),
        measured=False,
        formula=f"{persona_count}명 × {pages}페이지 × 가중치",
    )
