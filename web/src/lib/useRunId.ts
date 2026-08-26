import { useSearchParams } from 'react-router-dom'

/**
 * 지금 보고 있는 결과가 **어느 실행의 것인가**.
 *
 * 주소에 `?run=web_...` 이 붙어 있으면 로컬에서 방금 돌린 그 실행(agent-ux/logs/)을
 * 읽는다. 없으면 예전처럼 테스트 id 로 묻고, 데모에서는 번들된 기록이 답한다.
 *
 * 훅으로 둔 이유: 결과 화면은 표·다이어그램·페르소나 탭이 각자 따로 묻는다.
 * 값을 위에서부터 넘기면 컴포넌트 네 개의 인자가 늘어나는데, 이 값은 주소에
 * 이미 적혀 있으므로 필요한 자리에서 그냥 읽으면 된다.
 */
export function useRunId(): string | undefined {
  const [params] = useSearchParams()
  return params.get('run') || undefined
}
