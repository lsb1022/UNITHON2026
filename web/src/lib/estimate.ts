/**
 * 예상 소요·크레딧 공식.
 *
 *   소요(분) = 페르소나 수 × 2 × 1.2 × 0.88
 *   크레딧   = 페르소나 수          (1명당 1크레딧)
 *
 * 크레딧은 사람 수를 그대로 센다. 토큰으로 보여주던 것을 바꿨다 —
 * 토큰 수는 결제 단위가 아니라서, 그 숫자를 보고는 얼마가 빠지는지 알 수 없었다.
 *
 * 마법사 도중(아직 서버에 저장 전)에도 숫자를 보여줘야 해서 클라이언트에도 둔다.
 * 확인 화면은 서버가 계산한 값이 있으면 그것을 먼저 쓴다.
 */

/** 페르소나 한 명이 차지하는 실행 시간(분). 병렬 처리와 재시도까지 반영한 계수다. */
export const MINUTES_PER_PERSONA = 2 * 1.2 * 0.88

/** 페르소나 한 명 = 크레딧 한 개. */
export const CREDITS_PER_PERSONA = 1

export function estimateRun(personaCount: number) {
  const people = Math.max(0, personaCount)
  return {
    // 소수점을 그대로 보여주면 "21.12분"이 된다. 분 단위로 반올림해서 딱 떨어지게 둔다.
    minutes: Math.max(1, Math.round(people * MINUTES_PER_PERSONA)),
    credits: people * CREDITS_PER_PERSONA,
  }
}
