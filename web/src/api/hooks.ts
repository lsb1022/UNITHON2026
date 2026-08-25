import { useCallback, useEffect, useRef, useState } from 'react'
import { ApiError } from './client'

type QueryState<T> = {
  data: T | undefined
  loading: boolean
  error: string | null
  reload: () => void
}

/**
 * 조회용 최소 훅. react-query 를 넣을 만큼의 복잡도가 아직 없어서 직접 만든다.
 * 언마운트 뒤 setState 를 막고, deps 가 바뀌면 이전 응답을 버린다.
 */
export function useQuery<T>(fetcher: () => Promise<T>, deps: unknown[] = []): QueryState<T> {
  const [data, setData] = useState<T>()
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [nonce, setNonce] = useState(0)
  const alive = useRef(true)

  useEffect(() => {
    alive.current = true
    return () => {
      alive.current = false
    }
  }, [])

  useEffect(() => {
    let current = true
    setLoading(true)
    setError(null)

    fetcher()
      .then((result) => {
        if (!current || !alive.current) return
        setData(result)
      })
      .catch((cause: unknown) => {
        if (!current || !alive.current) return
        setError(cause instanceof ApiError ? cause.message : '불러오지 못했어요.')
      })
      .finally(() => {
        if (current && alive.current) setLoading(false)
      })

    return () => {
      current = false
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, nonce])

  const reload = useCallback(() => setNonce((n) => n + 1), [])

  return { data, loading, error, reload }
}

/** 쓰기용. 진행 상태와 실패 사유만 돌려준다. */
export function useMutation<Args extends unknown[], T>(action: (...args: Args) => Promise<T>) {
  const [pending, setPending] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const run = useCallback(
    async (...args: Args): Promise<T | null> => {
      setPending(true)
      setError(null)
      try {
        return await action(...args)
      } catch (cause) {
        setError(cause instanceof ApiError ? cause.message : '요청에 실패했어요.')
        return null
      } finally {
        setPending(false)
      }
    },
    [action],
  )

  return { run, pending, error }
}
