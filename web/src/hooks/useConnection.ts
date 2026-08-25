import { useCallback, useState } from 'react'
import { checkConnectivity } from '../api/client'
import type { ConnectionState } from '../components/ConnectionCard'

/** '연결하기' 버튼 하나의 상태. 새 프로젝트와 새 테스트가 같은 흐름을 쓴다. */
export function useConnection() {
  const [state, setState] = useState<ConnectionState>({ status: 'idle' })

  const run = useCallback(async (url: string) => {
    setState({ status: 'checking' })
    try {
      const result = await checkConnectivity(url)
      setState({ status: 'done', result })
    } catch (error) {
      // 검사 서버 자체가 안 떠 있는 경우와 사이트가 죽은 경우는 다른 문제다.
      setState({
        status: 'failed',
        message:
          error instanceof TypeError
            ? '연결 검사 서버에 닿지 못했어요. 백엔드(:8000)가 떠 있는지 확인해 주세요.'
            : ((error as Error).message ?? '연결 검사에 실패했어요.'),
      })
    }
  }, [])

  const reset = useCallback(() => setState({ status: 'idle' }), [])

  const result = state.status === 'done' ? state.result : null

  return {
    state,
    run,
    reset,
    /** 미리보기에 넘길 값들 */
    previewUrl: result?.final_url ?? result?.url ?? null,
    embeddable: result?.embeddable ?? false,
    blockReason: result?.embed_block_reason ?? null,
    connected: Boolean(result?.ok),
  }
}
