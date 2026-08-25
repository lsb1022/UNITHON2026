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
  embeddable: boolean | null
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

// --------------------------------------------------------------------------- //
// 테스트 상세 — 미션 경로 · 다이어그램 · 페르소나
// --------------------------------------------------------------------------- //

export type TestDetail = {
  id: string
  name: string
  device: string
  created_at: string
  project: { id: string; name: string; preview_url: string | null }
  mission: { prompt: string; success_criteria: string } | null
  persona_total: number
  journey_count: number
  /** 여정이 없으면 null — 화면이 "0.0%"라는 거짓 수치를 그리지 않도록. */
  success_rate: number | null
  drop_rate: number | null
  avg_success_steps: number | null
}

export type PathScreen = { key: string; title: string; url: string | null }

export type MissionPath = {
  rank: number
  name: string
  label: string
  persona_count: number
  step_count: number
  screens: PathScreen[]
  /** 카드에 다 못 실은 화면 수. 0이면 "+n" 을 그리지 않는다. */
  more: number
}

export type PathsPayload = {
  total: number
  success: { count: number; percent: number }
  drop: { count: number; percent: number }
  paths: { success: MissionPath[]; drop: MissionPath[] }
}

export type DiagramNode = {
  id: string
  column: number
  key: string
  title: string
  count: number
  success: number
  drop: number
}

export type DiagramPayload = {
  /** 열 하나 = 한 스텝. 한 열에 여러 화면이 동시에 설 수 있다. */
  columns: { index: number; label: string; nodes: DiagramNode[] }[]
  links: { source: string; target: string; count: number; success: number; drop: number }[]
  total: number
  /** 열 상한을 넘겨 끝까지 그리지 못한 인원. 조용히 버리면 전수를 본 것처럼 읽힌다. */
  truncated?: number
  max_columns?: number
}

/** 하나의 클릭. 좌표는 페이지 절대좌표라 화면 사진 위에 그대로 얹혀진다. */
export type StepClick = {
  x: number
  y: number
  w: number
  h: number
  label: string
  /** 눌렀는데 화면이 아무런 반응도 하지 않았다 — 헛클릭. */
  wasted: boolean
  persona: string
}

export type StepDot = { x: number; y: number; wasted: boolean }

export type StepPersona = {
  id: string
  label: string
  traits: Record<string, number>
  outcome: 'success' | 'drop'
  end_label: string
  total_steps: number
  /** 그 순간 이 사람이 무슨 생각으로 그것을 눌렀는지. */
  thought: string
  action: string
  target: string
  blocked: boolean
  /** 같은 단계에 다른 화면에 있었을 때만 채워진다. */
  screen?: string
  screen_title?: string
}

export type StepDetail = {
  id: string
  step: number
  screen: string
  title: string
  count: number
  shot: { src: string; w: number; h: number } | null
  clicks: StepClick[]
  /** 이 화면에서 벌어진 클릭 전부. 열지도의 바탕이 된다. */
  screen_clicks: StepDot[]
  wasted: number
  /** 이 단계에 이 화면에 있던 사람. */
  personas: StepPersona[]
  /** 같은 단계에 다른 화면에 있던 사람. */
  elsewhere: StepPersona[]
  /** 이 단계 전에 이미 끝난 사람. */
  finished: StepPersona[]
  /** 셋을 더하면 전체 인원이 된다. */
  total: number
}

export type FilmFrame = {
  step: number
  id: string
  title: string
  count: number
  shot: { src: string; w: number; h: number } | null
  /** 같은 단계에 다른 화면에 있었던 무리의 수. */
  others: number
}

export type PersonaOutcome = 'success' | 'drop' | 'other' | null

/** 한쪽 사이트에서의 결과. 기준(정상판)과 비교(결함판)를 나란히 놓기 위한 것. */
export type PersonaSideResult = {
  outcome: PersonaOutcome
  end_label: string
  step_count: number | null
  /** 그 사람이 밟은 화면 이름. A/B 상세 패널만 쓴다 — 없으면 경로를 그리지 않는다. */
  screens?: string[]
}

export type PersonaRow = {
  id: string
  code: string
  name: string
  age_band: string
  gender: string
  outcome: PersonaOutcome
  step_count: number | null
  /** 테스트 중 만들어진 행동 특성. 축마다 1~5단계. 사용자가 정하는 값이 아니다. */
  traits?: Record<string, number>
  /** 기준 사이트(정상판) 결과. 대조군이 없으면 null. */
  baseline?: PersonaSideResult | null
  /** 비교 사이트(결함판) 결과. */
  compare?: PersonaSideResult | null
  /** 두 사이트에서 결과가 갈렸는가. 이 사람들이 결함의 대가를 치른다. */
  changed?: boolean
}

/** 결과 화면이 어느 사이트 기준으로 볼지. 정상판(대조군) / 결함판. */
export type Variant = 'clean' | 'buggy'

/** ?variant= 를 붙인다. 고른 것이 없으면 서버가 기본값을 고른다. */
const withVariant = (path: string, variant?: Variant) =>
  variant ? `${path}?variant=${variant}` : path

export const getTest = (testId: string, variant?: Variant) =>
  request<TestDetail>(withVariant(`/api/tests/${testId}`, variant))

export const getTestPaths = (testId: string, variant?: Variant) =>
  request<PathsPayload>(withVariant(`/api/tests/${testId}/paths`, variant))

export const getTestDiagram = (testId: string, variant?: Variant) =>
  request<DiagramPayload>(withVariant(`/api/tests/${testId}/diagram`, variant))

export type PersonasPayload = {
  total: number
  items: PersonaRow[]
  /** 결과가 갈린 인원 · 스텝을 다 쓴 인원. 표 위 요약 칩에 쓴다. */
  changed?: number
  exhausted?: number
  baseline_run?: string | null
  compare_run?: string | null
  axes?: Record<string, string>
}

export const getTestPersonas = (testId: string, variant?: Variant) =>
  request<PersonasPayload>(withVariant(`/api/tests/${testId}/personas`, variant))

export type StepsPayload = {
  /** 막대 id → 그 막대를 눌렀을 때 보여줄 것. */
  steps: Record<string, StepDetail>
  /** 아래 필름 띄. 단계마다 사람이 가장 많았던 화면을 대표로 세운다. */
  filmstrip: FilmFrame[]
  /** 성격 문장표. 페르소나 규격의 원문이라 화면이 지어낼 일이 없다. */
  sentences: Record<string, Record<string, string>>
  axes: Record<string, string>
  test_name: string
}

export const getTestSteps = (testId: string, variant?: Variant) =>
  request<StepsPayload>(withVariant(`/api/tests/${testId}/steps`, variant))


// --------------------------------------------------------------------------- //
// 두 프로젝트 견주기
//
// 프로젝트 안에서는 자기 사이트 결과만 보여준다. 고치기 전과 고친 뒤를 나란히
// 놓는 일은 여기서만 한다 — 같은 사람 열 명을 양쪽에 똑같이 투입했기 때문에
// "이 사람이 못한 게 사이트 탓인지 역량 탓인지"가 이 표에서만 갈린다.
// --------------------------------------------------------------------------- //

export type CompareSide = {
  id: string
  name: string
  url: string
  success_rate: number | null
}

export type ComparePayload = {
  ok: boolean
  message?: string
  base?: CompareSide
  against?: CompareSide
  items: PersonaRow[]
  total?: number
  changed?: number
  exhausted?: number
  axes?: Record<string, string>
}

export const listComparableProjects = () =>
  request<CompareSide[]>('/api/compare/projects')

export const compareProjects = (base: string, against: string) =>
  request<ComparePayload>(`/api/compare?base=${base}&against=${against}`)

// --------------------------------------------------------------------------- //
// 계정 · 플랜 · 크레딧 (설정 / 크레딧 및 플랜 화면)
// --------------------------------------------------------------------------- //

export type Account = {
  name: string
  initial: string
  workspace: string
  email: string
  plan_label: string
}

export type PlanPayload = {
  current: {
    name: string
    price_label: string
    next_billing_at: string
    used: number
    quota: number
  }
  features: string[]
  upgrade: { badge: string; title: string; body: string; cta: string; note: string }
}

export type CreditsPayload = {
  balance: number
  used_this_month: number
  rules: { label: string; value: string; highlight: boolean }[]
  packs: { credits: number; price: string; featured: boolean }[]
  history: { at: string; label: string; delta: number }[]
}

export type PlanTier = {
  id: string
  name: string
  tagline: string
  price: string
  cta: string
  featured: boolean
  badge: string | null
  features: string[]
}

export const getAccount = () => request<Account>('/api/account')
export const getPlan = () => request<PlanPayload>('/api/billing/plan')
export const getCredits = () => request<CreditsPayload>('/api/billing/credits')
export const getPlanTiers = () => request<{ tiers: PlanTier[] }>('/api/billing/tiers')

// --------------------------------------------------------------------------- //
// A/B 테스트
// --------------------------------------------------------------------------- //

export type AbSide = {
  id: string
  name: string
  preview_url: string | null
  success_rate?: number | null
}

export type AbCard = {
  id: string
  name: string
  mission: string
  created_at: string
  a: AbSide
  b: AbSide
}

export type AbResult = {
  id: string
  name: string
  mission: string
  created_at: string
  a: AbSide
  b: AbSide
  compare:
    | { ok: true; items: PersonaRow[]; total?: number; changed?: number; exhausted?: number; axes?: Record<string, string> }
    | { ok: false; message: string; items: PersonaRow[] }
  diagrams: { a: DiagramPayload | null; b: DiagramPayload | null }
}

export const listAbTests = () => request<{ items: AbCard[] }>('/api/ab')

export const getAbTest = (id: string) => request<AbResult>(`/api/ab/${id}`)

export function createAbTest(body: {
  name: string
  a_project_id: string
  b_project_id: string
}) {
  return request<{ id?: string; error?: string }>('/api/ab', {
    method: 'POST',
    body: JSON.stringify(body),
  })
}
