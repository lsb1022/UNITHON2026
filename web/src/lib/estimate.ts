/**
 * 예상 소요·사용량 공식. 서버 `app/estimates.py` 와 같은 상수를 쓴다.
 *
 *   소요(분) = 페르소나 수 × 페이지 수 × MINUTES_WEIGHT
 *   토큰     = 페르소나 수 × 페이지 수 × TOKENS_WEIGHT
 *
 * 마법사 도중(아직 서버에 저장 전)에도 숫자를 보여줘야 해서 클라이언트에도 둔다.
 * 확인 화면은 서버가 계산한 값을 그대로 쓴다 — 저장된 답사 화면 수를 반영하기 때문이다.
 */
export const DEFAULT_PAGE_COUNT = 6
export const MINUTES_WEIGHT = 0.01
export const TOKENS_WEIGHT = 3_000

export function estimateRun(personaCount: number, pageCount = DEFAULT_PAGE_COUNT) {
  const pages = Math.max(1, pageCount)
  return {
    pageCount: pages,
    minutes: Math.max(1, Math.round(personaCount * pages * MINUTES_WEIGHT)),
    tokens: personaCount * pages * TOKENS_WEIGHT,
  }
}

/** 1,800,000 → "1.8M" · 45,000 → "45,000" */
export function formatTokens(tokens: number): string {
  if (tokens >= 1_000_000) return `${(tokens / 1_000_000).toFixed(1)}M`
  if (tokens >= 10_000) return `${Math.round(tokens / 1000).toLocaleString('ko-KR')}K`
  return tokens.toLocaleString('ko-KR')
}
