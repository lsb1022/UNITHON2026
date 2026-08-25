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
 * 끄려면 web/.env 에 VITE_MOCK=0 을 넣고 진짜 백엔드를 띄운다.
 */
import { MOCK_DATA } from './mock-data'

type Json = Record<string, unknown>

const PROJECT_ID = 'demo-moji'
const TEST_ID = 'demo-test'
const RUN_ID = 'demo-run'

/** 마법사가 앞뒤로 오가도 값이 남아 있어야 한다. 새로고침하면 초기화된다. */
const state = {
  missionPrompt: MOCK_DATA.goal as string,
  successCriteria: '주문 완료 화면에 도달하면 성공',
  personaTotal: 10,
  runStartedAt: 0,
  // 사용자가 입력한 주소를 기억한다. 무시하고 고정값을 보여주면
  // "내가 넣은 주소가 검사된 게 맞나?" 하는 의심이 남는다.
  projectName: 'MOJI STORE',
  targetUrl: 'http://localhost:8000/ux-testbed/flawed/index.html',
}

const runs = MOCK_DATA.runs as Record<string, {
  runId: string
  variant: string
  usage: { calls?: number; tokens_in?: number; tokens_out?: number; cost_usd?: number }
  personas: {
    id: string; label: string; steps: number; end: string; endLabel: string
    firstThought: string; lastThought: string
  }[]
}>

const primary = runs.buggy ?? runs.clean
const control = runs.clean

function rate(run?: typeof primary) {
  if (!run || run.personas.length === 0) return null
  const ok = run.personas.filter((p) => p.end === 'goal_reached').length
  return Math.round((ok / run.personas.length) * 1000) / 10
}

/** 실행 화면이 진행률을 그릴 수 있도록, 시작 시각 기준으로 흘려보낸다. */
function progress(): { done: number; total: number } {
  const total = primary?.personas.length ?? 10
  if (!state.runStartedAt) return { done: 0, total }
  const elapsed = (Date.now() - state.runStartedAt) / 1000
  // 실측: 페르소나 한 명이 대략 1~2분. 데모에서는 8초에 한 명씩 끝나는 속도로 보여준다.
  return { done: Math.min(total, Math.floor(elapsed / 8)), total }
}

const cleanMap = MOCK_DATA.maps.clean as { pages: { path: string; title: string }[] }

function project(): Json {
  return {
    id: PROJECT_ID,
    name: state.projectName,
    category: '커머스',
    test_count: 1,
    last_activity_at: MOCK_DATA.generatedAt,
    preview_url: state.targetUrl,
    preview_embeddable: true,
  }
}

const measured = MOCK_DATA.measured as {
  calls: number; tokensIn: number; tokensOut: number; usd: number; usdPerPersona: number
}

/**
 * 흉내 내지 않는 경로를 나타내는 표식.
 * `null` 을 그 뜻으로 쓰면 "실행 중인 것이 없다(null)"는 **정상 응답**과 구별되지 않아,
 * 그 응답이 진짜 서버로 새어 나간다 (실제로 /api/runs/active 가 그렇게 샜다).
 */
export const MOCK_MISS = Symbol('mock-miss')

/** 경로별 응답. 흉내 낼 수 없으면 MOCK_MISS 를 돌려 호출부가 진짜 서버로 넘기게 한다. */
export function mockResponse(path: string, init?: RequestInit): unknown {
  const method = (init?.method ?? 'GET').toUpperCase()
  const body = init?.body ? (JSON.parse(String(init.body)) as Json) : null

  if (path === '/api/connectivity/check') {
    const url = String(body?.url ?? '')
    if (url) state.targetUrl = url
    return {
      ok: true,
      url,
      final_url: url,
      status: 200,
      title: 'MOJI STORE',
      embeddable: true,
      embed_block_reason: null,
      link_count: cleanMap.pages.length,
      error_kind: null,
      message: '연결됐습니다. 화면 ' + cleanMap.pages.length + '종을 찾았습니다.',
    }
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
        issues: [{
          kind: 'judgement',
          message: `"${hit}" 는 결함을 미리 알려주는 표현입니다.`,
          fix: '무엇을 하려는지만 적어주세요. 예) 코튼 셔츠를 장바구니에 담아 주문까지 마친다',
        }],
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

  if (path === '/api/projects' && method === 'GET') return [project()]
  if (path === '/api/projects' && method === 'POST') {
    if (body?.name) state.projectName = String(body.name)
    if (body?.target_url) state.targetUrl = String(body.target_url)
    return project()
  }

  if (path === `/api/projects/${PROJECT_ID}`) {
    return {
      ...project(),
      device_preset: 'desktop',
      viewport: { w: 1280, h: 800 },
      success_rate: rate(primary),
      drop_rate: primary ? Math.round((100 - (rate(primary) ?? 0)) * 10) / 10 : null,
      variants: [
        { key: 'clean', label: '정상판(대조군)', base_url: state.targetUrl.replace('/flawed/', '/clean/'), is_control: true },
        { key: 'flawed', label: '결함판', base_url: state.targetUrl, is_control: false },
      ],
    }
  }

  if (path === `/api/projects/${PROJECT_ID}/tests` && method === 'GET') {
    return [{
      test_id: TEST_ID,
      name: '코튼 셔츠 주문 완주',
      created_at: MOCK_DATA.generatedAt,
      persona_count: primary?.personas.length ?? 0,
      success_rate: rate(primary),
      drop_rate: primary ? Math.round((100 - (rate(primary) ?? 0)) * 10) / 10 : null,
    }]
  }
  if (path === `/api/projects/${PROJECT_ID}/tests` && method === 'POST') return { id: TEST_ID }

  if (path === `/api/tests/${TEST_ID}/mission`) {
    state.missionPrompt = String(body?.prompt ?? state.missionPrompt)
    state.successCriteria = String(body?.success_criteria ?? state.successCriteria)
    return { id: 'demo-mission' }
  }

  if (path === `/api/tests/${TEST_ID}/persona-specs`) {
    const specs = (body as unknown as { total?: number }[]) ?? []
    state.personaTotal = specs.reduce((sum, s) => sum + (s.total ?? 0), 0) || state.personaTotal
    return { total: state.personaTotal }
  }

  if (path === `/api/tests/${TEST_ID}/personas/assemble`) {
    return { total: state.personaTotal }
  }

  if (path === `/api/tests/${TEST_ID}/review`) {
    const n = state.personaTotal
    return {
      project: { id: PROJECT_ID },
      test: { id: TEST_ID, name: '코튼 셔츠 주문 완주', device: 'desktop' },
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

  if (path === `/api/tests/${TEST_ID}/runs` && method === 'POST') {
    state.runStartedAt = Date.now()
    return { run_id: RUN_ID, persona_count: state.personaTotal, status: 'running' }
  }

  if (path === '/api/runs/active') {
    if (!state.runStartedAt) return null
    const { done, total } = progress()
    return {
      run_id: RUN_ID,
      project_id: PROJECT_ID,
      project_name: 'MOJI STORE',
      test_name: '코튼 셔츠 주문 완주',
      done,
      total,
    }
  }

  // 썸네일은 <img src> 로 직접 불려서 이 경로를 타지 않는다. 흉내 내지 않는다.
  return MOCK_MISS
}

/** 화면이 결과를 더 자세히 보여주고 싶을 때 쓰라고 열어둔다. */
export const demoRuns = { primary, control, measured, maps: MOCK_DATA.maps }
