/**
 * 백엔드 없이 도는 데모용 응답.
 *
 * 이 MVP 의 목적은 "이런 식으로 작동합니다"를 보여주는 것이라, 서버·DB 없이
 * 프론트 하나로 완결되게 만든다. 그래야 시연 중에 죽지 않고 정적 호스팅에도 올라간다.
 *
 * **숫자는 지어내지 않는다.** `mock-data.ts` 는 실제 파이프라인 실행 기록에서
 * 뽑아 넣은 값이고(agent-ux/export_web_mock.py), 여기서는 그것을 화면이 기대하는
 * 모양으로 옮기기만 한다. 실행을 다시 하면 내보내기만 다시 돌리면 된다.
 *
 * **주소 하나에 분석 하나.** 사이트 두 벌(clean/flawed)은 우리 실험용 사정이지
 * 사용자의 사정이 아니다. 사용자는 주소 하나를 넣었으므로 프로젝트 안에서는
 * 그 주소의 결과만 보여준다. 두 사이트를 견주는 일은 별도의 비교 화면에서만 한다.
 *
 * 끄려면 web/.env 에 VITE_MOCK=0 을 넣고 진짜 백엔드를 띄운다.
 */
import { MOCK_DATA } from './mock-data'

type Json = Record<string, unknown>

/**
 * 데모에 들어 있는 사이트 두 벌.
 *
 * 같은 쇼핑몰의 **고치기 전과 고친 뒤**로 세운다 — 비교 화면이 하려는 일이
 * 바로 그것이고, '결함판/정상판'은 우리 실험실 말이라 밖에서는 안 통한다.
 * `variant` 는 mock-data 안에서 어느 실행 기록을 꺼낼지 고르는 열쇠다.
 */
const SITES = [
  {
    id: 'moji-before',
    testId: 'moji-before-test',
    variant: 'buggy',
    name: 'MOJI STORE (개선 전)',
    url: 'http://localhost:8000/ux-testbed/flawed/index.html',
  },
  {
    id: 'moji-after',
    testId: 'moji-after-test',
    variant: 'clean',
    name: 'MOJI STORE (개선 후)',
    url: 'http://localhost:8000/ux-testbed/clean/index.html',
  },
  // 우리 테스트베드가 아닌 **진짜 공개 사이트**. 이 도구가 남의 사이트에도
  // 붙는다는 증거라 데모에 넣어 둔다. 사진은 없다 — 답사를 안 돌렸고,
  // 없는 것을 있는 척하지 않는다.
  {
    id: 'namu-wiki',
    testId: 'namu-wiki-test',
    variant: 'namu',
    name: '나무위키 (공개 사이트)',
    url: 'https://namu.wiki/',
  },
] as const

type Site = {
  id: string
  testId: string
  variant: string
  name: string
  url: string
}

/** 사이트마다 실제로 준 미션. 실행 기록에 남은 목표 그대로다. */
const MISSION: Record<string, { name: string; goal: string; criteria: string }> = {
  buggy: {
    name: '코튼 셔츠 주문 완주',
    goal: '코튼 셔츠를 장바구니에 담아 주문까지 마친다',
    criteria: '주문 완료 화면에 도달하면 성공',
  },
  clean: {
    name: '코튼 셔츠 주문 완주',
    goal: '코튼 셔츠를 장바구니에 담아 주문까지 마친다',
    criteria: '주문 완료 화면에 도달하면 성공',
  },
  namu: {
    name: '숭실대학교 지역 확인',
    goal: '숭실대학교를 검색해서 숭실대학교의 지역이 어디인지 파악한다',
    criteria: '숭실대학교 문서에 도달하고 화면에 "서울특별시"가 보이면 성공',
  },
}

const missionOf = (variant: string) => MISSION[variant] ?? MISSION.buggy

/** 주소가 어느 실행 기록에 해당하는지. 데모에 담긴 기록은 두 벌뿐이다. */
function variantOf(url: string): string {
  return url.includes('/clean/') ? 'clean' : 'buggy'
}

/**
 * 데모에 들어 있는 두 벌 + 사용자가 이 자리에서 만든 프로젝트.
 *
 * 사용자가 만든 것은 **따로 쌓는다**. 예전에는 주소가 겹치면 데모 프로젝트의
 * 이름을 갈아 끼웠는데, 새 프로젝트를 하나 만들었더니 원래 있던
 * 'MOJI STORE (개선 전)' 의 이름이 통째로 바뀌어 버렸다. 사용자가 만든 것이
 * 원래 있던 것을 건드리면 안 된다.
 */
function allSites(): Site[] {
  return [...(SITES as readonly Site[]), ...state.created]
}

const siteById = (id: string) => allSites().find((s) => s.id === id)
const siteByTest = (id: string) => allSites().find((s) => s.testId === id)

/**
 * 만든 프로젝트를 이 브라우저에 남긴다.
 *
 * 서버가 없으니 메모리에만 두면 새로고침 한 번에 방금 만든 프로젝트가 사라진다 —
 * 만들자마자 없어지는 건 데모라기보다 고장으로 보인다. 이 브라우저에만 남고
 * 다른 사람에게는 안 간다.
 *
 * 저장이 막힌 환경(사생활 보호 창, 사이트 데이터 차단)에서는 조용히 메모리만
 * 쓴다. 저장이 안 된다고 화면이 죽으면 안 된다.
 */
const STORE_KEY = 'moji.demo.projects'

function loadCreated(): Site[] {
  try {
    const raw = localStorage.getItem(STORE_KEY)
    const list = raw ? (JSON.parse(raw) as Site[]) : []
    return Array.isArray(list) ? list.filter((s) => s && s.id && s.url) : []
  } catch {
    return []
  }
}

function saveCreated(list: Site[]): void {
  try {
    localStorage.setItem(STORE_KEY, JSON.stringify(list))
  } catch {
    // 저장 못 해도 이번 세션에서는 동작한다.
  }
}

/** 마법사가 앞뒤로 오가도 값이 남아 있어야 한다. 새로고침하면 초기화된다. */
const state = {
  missionPrompt: MOCK_DATA.goal as string,
  successCriteria: '주문 완료 화면에 도달하면 성공',
  personaTotal: 10,
  /**
   * 이 자리에서 만든 프로젝트. 새로고침하면 사라진다 — 데모라 서버가 없다.
   * 결과는 주소에 맞는 실행 기록을 빌려 보여준다. 없는 숫자를 지어내는 것이
   * 아니라, 그 주소가 우리가 실제로 돌려본 두 사이트 중 하나이기 때문이다.
   */
  created: loadCreated(),
  targetUrl: SITES[0].url as string,
}

const nameOf = (site: Site) => site.name

const runs = MOCK_DATA.runs as Record<
  string,
  {
    runId: string
    variant: string
    usage: { calls?: number; tokens_in?: number; tokens_out?: number; cost_usd?: number }
    personas: {
      id: string
      label: string
      steps: number
      end: string
      endLabel: string
      firstThought: string
      lastThought: string
    }[]
  }
>

function rate(variant: string): number | null {
  const run = runs[variant]
  if (!run || run.personas.length === 0) return null
  const ok = run.personas.filter((p) => p.end === 'goal_reached').length
  return Math.round((ok / run.personas.length) * 1000) / 10
}

function dropRate(variant: string): number | null {
  const r = rate(variant)
  return r === null ? null : Math.round((100 - r) * 10) / 10
}

const cleanMap = MOCK_DATA.maps.clean as { pages: { path: string; title: string }[] }

/**
 * 입력창 앞의 "https://" 는 화면 장식일 뿐이라 값에 포함되지 않는다.
 * 그래서 사용자가 무엇을 치든(프로토콜 있든 없든) 열리는 주소로 맞춰준다.
 * localhost 는 http 다 — https 를 붙이면 연결이 안 된다.
 */
function normalizeUrl(raw: string): string {
  const t = raw.trim()
  if (!t) return ''
  if (/^https?:\/\//i.test(t)) return t
  const isLocal = /^(localhost|127\.0\.0\.1)(:|\/|$)/i.test(t)
  return (isLocal ? 'http://' : 'https://') + t
}

function projectCard(site: Site): Json {
  return {
    id: site.id,
    name: nameOf(site),
    category: '커머스',
    test_count: 1,
    last_activity_at: MOCK_DATA.generatedAt,
    preview_url: site.url,
    preview_embeddable: true,
  }
}

const measured = MOCK_DATA.measured as {
  calls: number
  tokensIn: number
  tokensOut: number
  usd: number
  usdPerPersona: number
}

const byVariant = MOCK_DATA.viewsByVariant as Record<
  string,
  {
    detail: Json
    paths: Json
    diagram: Json
    personas: Json
    steps: Json
    filmstrip: unknown[]
  }
>

/**
 * 흉내 내지 않는 경로를 나타내는 표식.
 * `null` 을 그 뜻으로 쓰면 "실행 중인 것이 없다(null)"는 **정상 응답**과 구별되지 않아,
 * 그 응답이 진짜 서버로 새어 나간다 (실제로 /api/runs/active 가 그렇게 샜다).
 */
export const MOCK_MISS = Symbol('mock-miss')


/**
 * 주소가 진짜 열리는지 **실제로 확인한다.**
 *
 * 예전에는 무엇을 넣든 "연결할 수 있어요 / HTTP 200 / 미리보기 가능"이라고
 * 답했다. 있지도 않은 `ㅗㅗㅗ.com` 도 통과했다. 확인해준다고 해놓고 확인하지
 * 않는 것은 없는 기능보다 나쁘다 — 사용자가 그 말을 믿고 다음 단계로 간다.
 *
 * 브라우저에서 남의 주소의 **상태 코드**까지는 알 수 없다(CORS). 하지만
 * `no-cors` 로 던져보면 **닿는지 안 닿는지**는 알 수 있다: 없는 도메인이나
 * 죽은 서버는 예외를 던지고, 살아 있으면 내용은 못 읽어도 성공으로 돌아온다.
 * 알 수 있는 것만 말하고 나머지는 모른다고 말한다.
 */
const PROBE_MS = 8000

async function checkUrl(url: string) {
  if (!url) {
    return {
      ok: false, url, final_url: null, status: null, title: null,
      embeddable: false, embed_block_reason: null, link_count: null,
      error_kind: 'empty', message: '주소를 입력해 주세요.',
    }
  }

  let host = ''
  try {
    host = new URL(url).hostname
  } catch {
    return {
      ok: false, url, final_url: null, status: null, title: null,
      embeddable: false, embed_block_reason: null, link_count: null,
      error_kind: 'malformed', message: '주소 형식이 올바르지 않아요.',
    }
  }
  if (!host.includes('.') && host !== 'localhost') {
    return {
      ok: false, url, final_url: null, status: null, title: null,
      embeddable: false, embed_block_reason: null, link_count: null,
      error_kind: 'malformed',
      message: `"${host}" 는 주소로 보이지 않아요. 예) www.example.com`,
    }
  }

  const known = SITES.find((s) => url.startsWith(s.url.replace('/index.html', '')))
  const started = Date.now()
  try {
    const ctl = new AbortController()
    const timer = setTimeout(() => ctl.abort(), PROBE_MS)
    // no-cors 라 내용을 못 읽는다. 우리가 얻는 것은 '닿았다'는 사실 하나뿐이다.
    await fetch(url, { mode: 'no-cors', signal: ctl.signal, cache: 'no-store' })
    clearTimeout(timer)
  } catch {
    return {
      ok: false, url, final_url: null, status: null, title: null,
      embeddable: false, embed_block_reason: null, link_count: null,
      error_kind: 'unreachable',
      message: `${host} 에 닿지 못했어요. 주소가 맞는지, 사이트가 열려 있는지 확인해 주세요.`,
    }
  }

  return {
    ok: true,
    url,
    final_url: url,
    // 상태 코드는 브라우저에서 읽을 수 없다. 200 이라고 적으면 거짓말이 된다.
    status: null,
    title: known ? 'MOJI STORE' : null,
    // 미리보기(iframe) 가능 여부도 여기서는 알 수 없다. 큰 사이트는 대부분
    // 막아둔다. 열어보고 안 되면 그때 대체 화면을 보여준다.
    embeddable: null,
    embed_block_reason: null,
    // 링크 수는 답사를 돌려야 나온다. 아는 사이트만 말한다.
    link_count: known ? cleanMap.pages.length : null,
    error_kind: null,
    elapsed_ms: Date.now() - started,
    message: known
      ? `연결됐습니다. 화면 ${cleanMap.pages.length}종을 찾았습니다.`
      : `${host} 에 닿았습니다. 화면이 몇 종인지는 답사를 돌려야 알 수 있어요.`,
  }
}

/** 경로별 응답. 흉내 낼 수 없으면 MOCK_MISS 를 돌려 호출부가 진짜 서버로 넘기게 한다. */
export function mockResponse(rawPath: string, init?: RequestInit): unknown {
  const method = (init?.method ?? 'GET').toUpperCase()
  const body = init?.body ? (JSON.parse(String(init.body)) as Json) : null
  const [path, query = ''] = rawPath.split('?')
  const params = new URLSearchParams(query)

  if (path === '/api/connectivity/check') {
    const url = normalizeUrl(String(body?.url ?? ''))
    if (url) state.targetUrl = url
    return checkUrl(url)
  }

  if (path === '/api/missions/analyze') {
    const prompt = String(body?.prompt ?? '')
    // 답사자에게 걸었던 것과 같은 규칙이다. 목표에 결함을 적으면 100명 전원이
    // 그것을 찾으러 가고, 적중률이 우리가 알려준 답을 세는 값이 된다.
    const banned = ['작동하지', '안 됨', '문제', '오류', '불편', '이상']
    const hit = banned.find((w) => prompt.includes(w))
    if (hit) {
      return {
        status: 'invalid',
        success_criteria: null,
        issues: [
          {
            kind: 'judgement',
            message: `"${hit}" 는 결함을 미리 알려주는 표현입니다.`,
            fix: '무엇을 하려는지만 적어주세요. 예) 코튼 셔츠를 장바구니에 담아 주문까지 마친다',
          },
        ],
        generated_by: 'rule',
      }
    }
    return {
      status: 'ok',
      success_criteria: state.successCriteria,
      issues: [],
      generated_by: 'rule',
    }
  }

  // ── 프로젝트 ──────────────────────────────────────────────────
  if (path === '/api/projects' && method === 'GET') return allSites().map(projectCard)
  if (path === '/api/projects' && method === 'POST') {
    // **새 항목으로 쌓는다.** 원래 있던 데모 프로젝트는 건드리지 않는다.
    const url = normalizeUrl(String(body?.target_url ?? state.targetUrl))
    state.targetUrl = url
    // 지운 뒤 다시 만들어도 id 가 겹치지 않도록 지금 있는 것 중 가장 큰 번호 다음을 쓴다.
    const used = state.created
      .map((s) => Number(s.id.replace('made-', '')))
      .filter((n) => Number.isFinite(n))
    const n = (used.length ? Math.max(...used) : 0) + 1
    const site: Site = {
      id: `made-${n}`,
      testId: `made-${n}-test`,
      variant: variantOf(url),
      name: String(body?.name || `새 프로젝트 ${n}`),
      url,
    }
    state.created.push(site)
    saveCreated(state.created)
    return projectCard(site)
  }

  const project = allSites().find((s) => path === `/api/projects/${s.id}`)
  if (project) {
    return {
      ...projectCard(project),
      device_preset: 'desktop',
      viewport: { w: 1280, h: 800 },
      success_rate: rate(project.variant),
      drop_rate: dropRate(project.variant),
    }
  }

  const listing = allSites().find((s) => path === `/api/projects/${s.id}/tests`)
  if (listing) {
    if (method === 'POST') return { id: listing.testId }
    return [
      {
        test_id: listing.testId,
        name: missionOf(listing.variant).name,
        created_at: MOCK_DATA.generatedAt,
        persona_count: runs[listing.variant]?.personas.length ?? 0,
        success_rate: rate(listing.variant),
        drop_rate: dropRate(listing.variant),
      },
    ]
  }

  // ── 결과 화면 ────────────────────────────────────────────────
  // 숫자는 전부 실제 실행 기록에서 뽑은 것이다 (agent-ux/export_web_mock.py).
  // 프로젝트 하나는 사이트 하나다 — 어느 쪽을 볼지 고르는 스위치는 없다.
  const site = siteByTest(path.split('/')[3] ?? '')
  if (site) {
    const base = `/api/tests/${site.testId}`
    const views = byVariant[site.variant]

    // 마법사가 저장하는 것들. 데모라 받아만 두고 흘려보낸다.
    if (path === `${base}/mission`) {
      state.missionPrompt = String(body?.prompt ?? state.missionPrompt)
      state.successCriteria = String(body?.success_criteria ?? state.successCriteria)
      return { id: 'demo-mission' }
    }
    if (path === `${base}/persona-specs`) {
      const specs = (body as unknown as { total?: number }[]) ?? []
      state.personaTotal = specs.reduce((sum, s) => sum + (s.total ?? 0), 0) || state.personaTotal
      return { total: state.personaTotal }
    }
    if (path === `${base}/personas/assemble`) return { total: state.personaTotal }

    if (path === `${base}/review`) {
      const n = state.personaTotal
      return {
        project: { id: site.id },
        test: { id: site.testId, name: missionOf(site.variant).name, device: 'desktop' },
        mission: { prompt: state.missionPrompt, success_criteria: state.successCriteria },
        personas: {
          total: n,
          // 화면은 연령대 표를 그리지만 우리 페르소나는 특성 축으로 나뉜다.
          // 없는 값을 지어내지 않고, 축 이름을 그대로 칸 이름으로 쓴다.
          breakdown: Object.entries(MOCK_DATA.axisDistribution).map(([axis, dist]) => {
            const counts = Object.values(dist as Record<string, number>)
            const low = (counts[0] ?? 0) + (counts[1] ?? 0)
            const high = (counts[3] ?? 0) + (counts[4] ?? 0)
            return {
              age_band: (MOCK_DATA.axes as Record<string, string>)[axis] ?? axis,
              total: counts.reduce((a, b) => a + b, 0),
              male: low,
              female: high,
              any: counts[2] ?? 0,
            }
          }),
        },
        estimate: {
          minutes: Math.max(1, Math.round(n * 1.5)),
          tokens: measured.tokensIn + measured.tokensOut,
          page_count: cleanMap.pages.length,
          vision_calls: (MOCK_DATA.maps.clean as { shots: number }).shots,
          usd: Math.round(measured.usdPerPersona * n * 10000) / 10000,
          measured: true,
          formula: `실측 1인당 $${measured.usdPerPersona} × ${n}명 (답사는 1회만, 이미지 ${(MOCK_DATA.maps.clean as { shots: number }).shots}장)`,
        },
      }
    }

    if (views) {
      if (path === base) {
        const m = missionOf(site.variant)
        return {
          id: site.testId,
          name: m.name,
          device: 'desktop',
          created_at: MOCK_DATA.generatedAt,
          project: { id: site.id, name: nameOf(site), preview_url: site.url },
          mission: { prompt: m.goal, success_criteria: m.criteria },
          ...views.detail,
        }
      }
      if (path === `${base}/paths`) return views.paths
      if (path === `${base}/diagram`) return views.diagram
      if (path === `${base}/personas`) return views.personas
      // 막대를 눌렀을 때 뜨는 단계 상세. 성격 문장은 페르소나 규격의
      // 원문을 그대로 내려보낸다 — 화면이 사람 성격을 지어내지 않도록.
      if (path === `${base}/steps`) {
        return {
          steps: views.steps,
          filmstrip: views.filmstrip,
          sentences: MOCK_DATA.axisSentences,
          axes: MOCK_DATA.axes,
          test_name: missionOf(site.variant).name,
        }
      }
    }
  }

  // ── 두 프로젝트 견주기 ────────────────────────────────────────
  // 프로젝트 안에서는 자기 결과만 보여주고, 두 사이트를 나란히 놓는 일은
  // 여기서만 한다. 같은 사람 열 명을 양쪽에 똑같이 투입했기 때문에 성립한다.
  if (path === '/api/compare/projects') {
    return allSites().map((s) => ({
      id: s.id,
      name: nameOf(s),
      url: s.url,
      success_rate: rate(s.variant),
    }))
  }

  if (path === '/api/compare') {
    const left = siteById(params.get('base') ?? '')
    const right = siteById(params.get('against') ?? '')
    if (!left || !right || left.id === right.id) {
      return { ok: false, message: '서로 다른 프로젝트 두 개를 골라주세요.', items: [] }
    }
    // 내보낸 표에서 baseline 은 대조군, compare 는 그 실행 자신이다.
    // 그래서 '비교 사이트' 기준의 표를 꺼내면 baseline 이 곧 '기준 사이트'가 된다.
    const table = byVariant[right.variant]?.personas as
      | { items?: unknown[]; total?: number; changed?: number; exhausted?: number; axes?: Json }
      | undefined
    if (!table) return { ok: false, message: '아직 비교할 기록이 없어요.', items: [] }
    return {
      ok: true,
      base: { id: left.id, name: nameOf(left), url: left.url, success_rate: rate(left.variant) },
      against: {
        id: right.id,
        name: nameOf(right),
        url: right.url,
        success_rate: rate(right.variant),
      },
      ...table,
    }
  }

  // 실행과 진행률만은 흉내 내지 않는다. 진짜 파이프라인이 답사부터 돌고,
  // 진행률은 logs/ 에 쌓인 기록 파일 수에서 나온다.
  // (agent-ux/server.py 를 띄우고 VITE_API_BASE 를 그쪽으로 두면 연결된다)
  if (path.endsWith('/runs') && method === 'POST') return MOCK_MISS
  if (path === '/api/runs/active') return MOCK_MISS

  // 썸네일은 <img src> 로 직접 불려서 이 경로를 타지 않는다. 흉내 내지 않는다.
  return MOCK_MISS
}

/** 화면이 결과를 더 자세히 보여주고 싶을 때 쓰라고 열어둔다. */
export const demoRuns = { runs, measured, maps: MOCK_DATA.maps, sites: SITES }
