"""프로젝트 카테고리 목록.

자유 입력이면 "쇼핑몰"과 "커머스"가 서로 다른 그룹이 되어 카테고리별 묶기가 무의미해진다.
목록을 여기 한 곳에 두고 API 가 검증한다. 화면 쪽 목록은
`web/src/components/CategorySelect.tsx` 에 같은 순서로 있다 — 둘이 어긋나면
사용자가 고른 값을 서버가 거부하므로, 바꿀 때는 반드시 양쪽을 함께 고칠 것.
"""

from __future__ import annotations

CATEGORIES: tuple[str, ...] = (
    "커머스",
    "푸드",
    "미디어",
    "트래블",
    "헬스",
    "금융",
    "교육",
    "생산성",
    "기타",
)

#: 예전 자유 입력 시절 값과 흔한 동의어를 정규화한다.
ALIASES: dict[str, str] = {
    "쇼핑몰": "커머스",
    "쇼핑물": "커머스",
    "이커머스": "커머스",
    "e커머스": "커머스",
    "commerce": "커머스",
    "음식": "푸드",
    "food": "푸드",
    "여행": "트래블",
    "travel": "트래블",
    "건강": "헬스",
    "health": "헬스",
    "핀테크": "금융",
}


def normalize(value: str) -> str | None:
    """알려진 카테고리로 맞춘다. 맞출 수 없으면 None — 호출부가 400을 낸다."""
    text = value.strip()
    if text in CATEGORIES:
        return text
    return ALIASES.get(text) or ALIASES.get(text.lower())
