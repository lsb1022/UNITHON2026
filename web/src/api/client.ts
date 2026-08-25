import { MOCK_MISS, mockResponse } from './mock'

const BASE = import.meta.env.VITE_API_BASE ?? 'http://localhost:8000'

/**
 * 데모 모드. 백엔드 없이 프론트 하나로 돌린다 (MVP 광고용).
 * 진짜 백엔드에 붙이려면 web/.env 에 VITE_MOCK=0 을 넣는다.
 */
const USE_MOCK = (import.meta.env.VITE_MOCK ?? '1') !== '0'

/** fetch 를 거치지 않는 것(예: <img src>)도 서버 주소가 필요하다. */
export const API_BASE = BASE

/** 서버가 돌려준 오류를 화면이 그대로 보여줄 수 있는 형태로 감싼다. */
export class ApiError extends Error {
  // 생성자 파라미터 프로퍼티는 erasableSyntaxOnly 에서 막히므로 필드로 따로 둔다.
  status: number

  constructor(message: string, status: number) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  if (USE_MOCK) {
    const canned = mockResponse(path, init)
    // 흉내 낼 수 없는 경로만 진짜 서버로 넘긴다. null 은 그 자체가 정상 응답일 수 있다
    // (예: 실행 중인 것이 없으면 /api/runs/active 는 null 을 돌려준다).
    if (canned !== MOCK_MISS) {
      // 실제 호출처럼 보이도록 한 박자 쉰다. 로딩 상태가 화면에서 사라지지 않도록.
      await new Promise((r) => setTimeout(r, 180))
      return canned as T
    }
  }

  let response: Response
  try {
    response = await fetch(`${BASE}${path}`, {
      headers: init?.body ? { 'Content-Type': 'application/json' } : undefined,
      ...init,
    })
  } catch {
    // 서버가 안 떠 있는 경우와 서버가 에러를 준 경우는 사용자가 할 일이 다르다.
    throw new ApiError(`API 서버(${BASE})에 닿지 못했어요. 백엔드가 떠 있는지 확인해 주세요.`, 0)
  }

  if (!response.ok) {
    const detail = await response
      .json()
      .then((body) => (typeof body?.detail === 'string' ? body.detail : null))
      .catch(() => null)
    throw new ApiError(detail ?? `요청이 실패했어요 (HTTP ${response.status})`, response.status)
  }

  if (response.status === 204) return undefined as T
  return response.json()
}

// --------------------------------------------------------------------------- //
// 연결 검사
// --------------------------------------------------------------------------- //

export type ConnectivityResult = {
  ok: boolean
  url: string
  final_url: string | null
  status: number | null
  title: string | null
  /** 도달 가능 여부와 별개다. 열리지만 iframe 임베드만 막는 사이트가 흔하다. */
  embeddable: boolean
  embed_block_reason: string | null
  link_count: number | null
  error_kind: string | null
  message: string
}

export function checkConnectivity(url: string) {
  return request<ConnectivityResult>('/api/connectivity/check', {
    method: 'POST',
    body: JSON.stringify({ url }),
  })
}

// --------------------------------------------------------------------------- //
// 미션 분석
// --------------------------------------------------------------------------- //

export type MissionIssue = { kind: string; message: string; fix: string }

export type MissionAnalysis = {
  /** ok = 그대로 써도 됨 · warning = 고치면 더 좋음 · invalid = 이대로는 못 돌림 */
  status: 'ok' | 'warning' | 'invalid'
  success_criteria: string | null
  issues: MissionIssue[]
  generated_by: string
}

export function analyzeMission(prompt: string) {
  return request<MissionAnalysis>('/api/missions/analyze', {
    method: 'POST',
    body: JSON.stringify({ prompt }),
  })
}

// --------------------------------------------------------------------------- //
// 프로젝트
// --------------------------------------------------------------------------- //

export type ProjectCard = {
  id: string
  name: string
  category: string
  test_count: number
  last_activity_at: string
  /** 카드 썸네일에 띄울 실제 주소. 임베드가 막힌 사이트면 대체 이미지를 쓴다. */
  preview_url: string | null
  preview_embeddable: boolean
}

export type ProjectDetail = {
  id: string
  name: string
  category: string
  device_preset: string
  viewport: { w: number; h: number }
  test_count: number
  /** 여정이 하나도 없으면 null — 화면이 "0.0%"라는 거짓 수치를 그리지 않도록. */
  success_rate: number | null
  drop_rate: number | null
  preview_url: string | null
  preview_embeddable: boolean
  variants: { key: string; label: string; base_url: string; is_control: boolean }[]
}

export type TestStats = {
  test_id: string
  name: string
  created_at: string
  persona_count: number
  success_rate: number | null
  drop_rate: number | null
}

export const listProjects = () => request<ProjectCard[]>('/api/projects')

export const getProject = (id: string) => request<ProjectDetail>(`/api/projects/${id}`)

export const listTests = (projectId: string) =>
  request<TestStats[]>(`/api/projects/${projectId}/tests`)

export function createProject(body: {
  name: string
  category: string
  target_url: string
  source?: string
  device_preset?: string
  flow_map_path?: string | null
  preview_embeddable?: boolean
}) {
  return request<ProjectCard>('/api/projects', { method: 'POST', body: JSON.stringify(body) })
}

// --------------------------------------------------------------------------- //
// 테스트 마법사
// --------------------------------------------------------------------------- //

export function createTest(
  projectId: string,
  body: { name: string; device: string; target_url: string },
) {
  return request<{ id: string }>(`/api/projects/${projectId}/tests`, {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

export function saveMission(
  testId: string,
  body: { prompt: string; success_criteria: string; auto_detect?: boolean },
) {
  return request<{ id: string }>(`/api/tests/${testId}/mission`, {
    method: 'PUT',
    body: JSON.stringify(body),
  })
}

export type PersonaSpecPayload = {
  age_band: string
  total: number
  female_percent?: number
  gender_agnostic?: boolean
  enabled?: boolean
}

export function savePersonaSpecs(testId: string, specs: PersonaSpecPayload[]) {
  return request<{ total: number }>(`/api/tests/${testId}/persona-specs`, {
    method: 'PUT',
    body: JSON.stringify(specs),
  })
}

export type ReviewPayload = {
  project: { id: string }
  test: { id: string; name: string; device: string }
  mission: { prompt: string; success_criteria: string } | null
  personas: {
    total: number
    breakdown: { age_band: string; total: number; male: number; female: number; any: number }[]
  }
  estimate: {
    minutes: number
    tokens: number
    page_count: number
    vision_calls: number
    usd: number
    measured: boolean
    formula: string
  }
}

export const getReview = (testId: string) => request<ReviewPayload>(`/api/tests/${testId}/review`)

export const startRun = (testId: string) =>
  request<{ run_id: string; persona_count: number; status: string }>(`/api/tests/${testId}/runs`, {
    method: 'POST',
  })

// --------------------------------------------------------------------------- //
// 실행중
// --------------------------------------------------------------------------- //

export type ActiveRun = {
  run_id: string
  project_id: string
  project_name: string
  test_name: string
  done: number
  total: number
}

export const getActiveRun = () => request<ActiveRun | null>('/api/runs/active')
