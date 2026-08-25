import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { API_BASE, getActiveRun, getProject, type ActiveRun } from '../api/client'
import { useQuery } from '../api/hooks'
import arrowIcon from '../assets/icons/arrow.svg'
import { AppLayout, PageBody } from '../components/AppLayout'
import { WizardTopBar } from '../components/StepIndicator'
import { estimateRun } from '../lib/estimate'
import { useWizard } from '../state/WizardContext'

/** 진행 상황을 얼마나 자주 다시 물을지. 파이프라인이 여정을 채우는 속도 기준. */
const POLL_MS = 3000

export function RunningPage() {
  const { projectId = '' } = useParams()
  const navigate = useNavigate()
  const { testName } = useWizard()

  const project = useQuery(() => getProject(projectId), [projectId])
  const [run, setRun] = useState<ActiveRun | null>(null)

  useEffect(() => {
    let alive = true

    const tick = async () => {
      try {
        const next = await getActiveRun()
        if (alive) setRun(next)
      } catch {
        // 폴링 실패는 화면을 깨뜨리지 않는다. 다음 주기에 다시 시도한다.
      }
    }

    void tick()
    const timer = window.setInterval(tick, POLL_MS)
    return () => {
      alive = false
      window.clearInterval(timer)
    }
  }, [])

  const done = run?.done ?? 0
  const total = run?.total ?? 0
  const percent = total > 0 ? Math.round((done / total) * 100) : 0
  const name = run?.test_name ?? testName
  const projectName = run?.project_name ?? project.data?.name ?? ''

  // 남은 시간 = 전체 예상 시간 × 남은 비율. 실측이 아니라 공식이라 '예상'을 붙인다.
  const remaining = total > 0 ? Math.max(0, Math.round(estimateRun(total).minutes * (1 - done / total))) : null

  return (
    <AppLayout
      topBar={<WizardTopBar breadcrumb={{ project: projectName, page: name }} current={4} />}
    >
      <PageBody className="pt-[56px]">
        <div className="mx-auto flex max-w-[1402px] flex-col items-center">
          <LoadingRing />

          <p className="mt-[32px] flex items-baseline gap-[8px] whitespace-nowrap">
            <span className="text-[24px] leading-[1.45] font-bold text-ink">
              {projectName} / {name}
            </span>
            <span className="text-[20px] leading-[1.45] text-ink">
              {run ? '진행중' : '대기중'}
            </span>
          </p>

          <div className="mt-[28px] w-full">
            <p className="text-[36px] leading-[1.45] font-bold text-ink tabular-nums">{percent}%</p>
            <div
              role="progressbar"
              aria-valuenow={percent}
              aria-valuemin={0}
              aria-valuemax={100}
              className="mt-[12px] h-[14px] w-full overflow-hidden rounded-[7px] bg-track"
            >
              <div
                className="h-full rounded-[7px] bg-main transition-[width] duration-500"
                style={{ width: `${percent}%` }}
              />
            </div>
            <div className="mt-[22px] flex justify-end gap-[38px] text-[15px] text-subtext">
              <span>
                {done} / {total}명이 테스트를 마쳤어요
              </span>
              {remaining !== null ? <span>예상 {remaining}분 남음</span> : null}
            </div>
          </div>

          <button
            type="button"
            onClick={() => navigate(`/projects/${projectId}`)}
            className="mt-[44px] flex h-[76px] w-[316px] items-center justify-center gap-[10px] rounded-[16px] border border-ink bg-white text-[24px] leading-[1.45] font-bold text-ink transition-colors hover:bg-black/[0.03]"
          >
            프로젝트로 돌아가기
            <img src={arrowIcon} alt="" aria-hidden className="size-[15px] invert" />
          </button>

          {/* [임시] 답사자가 본 화면.
              첫 페르소나만 스크린샷을 찍어 사이트 설명서를 만들고, 뒤따르는
              페르소나들은 이미지 없이 그 설명서와 계산된 수치만 읽는다.
              그 차이를 눈으로 확인하라고 열어둔 통로다. 결과 화면이 생기면
              그쪽으로 옮긴다. */}
          <a
            href={`${API_BASE}/shots`}
            target="_blank"
            rel="noreferrer"
            className="mt-[14px] text-[15px] text-subtext underline underline-offset-4 hover:text-ink"
          >
            답사자가 본 화면 보기 (스크린샷)
          </a>
        </div>
      </PageBody>
    </AppLayout>
  )
}

// 디자인은 1920×1080 기준 395px. 노트북 높이에서 스크롤이 생기지 않도록 줄였다.
const RING_SIZE = 300
const RING_STROKE = 14

/**
 * 무한 회전 로딩 링.
 *
 * 진행률은 아래 진행바가 이미 정확히 보여준다. 이 링은 "지금 돌고 있다"만 말하는
 * 장식이라 값과 묶지 않는다 — 값에 묶으면 68%에서 멈춰 선 것처럼 보인다.
 */
function LoadingRing() {
  const radius = (RING_SIZE - RING_STROKE) / 2

  return (
    <svg
      width={RING_SIZE}
      height={RING_SIZE}
      viewBox={`0 0 ${RING_SIZE} ${RING_SIZE}`}
      role="status"
      aria-label="테스트 진행중"
      className="loading-ring"
    >
      <circle
        cx={RING_SIZE / 2}
        cy={RING_SIZE / 2}
        r={radius}
        fill="none"
        stroke="var(--color-track)"
        strokeWidth={RING_STROKE}
      />
      <circle
        className="loading-ring__arc"
        cx={RING_SIZE / 2}
        cy={RING_SIZE / 2}
        r={radius}
        fill="none"
        stroke="var(--color-main)"
        strokeOpacity={0.45}
        strokeWidth={RING_STROKE}
        strokeLinecap="round"
      />
    </svg>
  )
}
