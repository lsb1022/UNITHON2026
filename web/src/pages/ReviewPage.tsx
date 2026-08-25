import { useNavigate, useParams } from 'react-router-dom'
import { getProject, getReview, startRun } from '../api/client'
import { useMutation, useQuery } from '../api/hooks'
import checkMarkBlue from '../assets/icons/check-mark-blue.svg'
import { AppLayout, PageBody } from '../components/AppLayout'
import { WizardTopBar } from '../components/StepIndicator'
import { ErrorBlock, LoadingBlock } from '../components/StateView'
import { estimateRun, formatTokens } from '../lib/estimate'
import { splitRow, useWizard } from '../state/WizardContext'

export function ReviewPage() {
  const { projectId = '' } = useParams()
  const navigate = useNavigate()
  const { testId, testName, mission, rows, totalPersonas, rowTotal } = useWizard()

  const project = useQuery(() => getProject(projectId), [projectId])
  // 테스트가 저장돼 있으면 서버 계산을 그대로 쓴다 (답사 화면 수가 반영된 값).
  const review = useQuery(
    () => (testId ? getReview(testId) : Promise.resolve(null)),
    [testId],
  )
  const start = useMutation(startRun)

  const local = estimateRun(totalPersonas)
  const est = review.data?.estimate
  const minutes = est?.minutes ?? local.minutes
  const tokens = est?.tokens ?? local.tokens
  const pageCount = est?.page_count ?? local.pageCount
  const total = review.data?.personas.total ?? totalPersonas

  if (project.loading) {
    return (
      <AppLayout>
        <PageBody>
          <LoadingBlock />
        </PageBody>
      </AppLayout>
    )
  }

  if (project.error || !project.data) {
    return (
      <AppLayout>
        <PageBody>
          <ErrorBlock message={project.error ?? '프로젝트가 없어요'} onRetry={project.reload} />
        </PageBody>
      </AppLayout>
    )
  }

  const breakdown = review.data?.personas.breakdown ?? null

  return (
    <AppLayout
      topBar={<WizardTopBar breadcrumb={{ project: project.data.name, page: testName }} current={4} />}
      footer={
        <>
          <button
            type="button"
            onClick={() => navigate(`/projects/${projectId}/tests/new/persona`)}
            className="h-[65px] w-[179px] rounded-[14px] border border-line bg-white text-[20px] leading-[1.45] font-medium text-heading transition-colors hover:bg-black/[0.03]"
          >
            이전
          </button>
          <button
            type="button"
            disabled={start.pending || !testId}
            onClick={async () => {
              if (!testId) return
              const run = await start.run(testId)
              if (run) navigate(`/projects/${projectId}/tests/new/running`)
            }}
            className="flex h-[65px] w-[179px] items-center justify-center gap-[5px] rounded-[14px] bg-main text-[20px] leading-[1.45] font-medium text-white transition-colors hover:bg-[#2872dd] disabled:cursor-not-allowed disabled:bg-[#c4d9f9]"
          >
            {start.pending ? '시작하는 중…' : '테스트 하기 →'}
          </button>
        </>
      }
    >
      <PageBody>
        <div className="flex gap-[30px]">
          <div className="min-w-0 max-w-[920px] flex-1">
            <h1 className="text-[34px] leading-[1.45] font-bold text-heading">
              이대로 <span className="text-main">{testName}</span>를 시작할까요?
            </h1>
            <p className="mt-[8px] text-[16px] leading-[1.45] text-subtext">
              설정을 한 번 확인하고 바로 시작할 수 있어요.
            </p>

            {start.error ? (
              <p className="mt-[16px] text-[14px] font-medium text-danger">{start.error}</p>
            ) : null}

            <div className="mt-[43px] rounded-[22px] border border-line bg-white px-[24px]">
              <SummarySection title="테스트 대상 프로젝트">
                <p className="pl-[19px] text-[16px] leading-[1.45] font-bold text-heading">
                  {project.data.name}
                </p>
              </SummarySection>

              <SummarySection
                title="미션"
                onEdit={() => navigate(`/projects/${projectId}/tests/new/mission`)}
              >
                <p className="pl-[18px] text-[16px] leading-[1.45] font-bold text-heading">
                  {review.data?.mission?.prompt ?? mission}
                </p>
              </SummarySection>

              <SummarySection
                title="페르소나"
                last
                onEdit={() => navigate(`/projects/${projectId}/tests/new/persona`)}
              >
                <div className="flex flex-col gap-[14px] pl-[23px]">
                  <p className="text-[16px] leading-[1.45] font-bold text-heading">총 {total}명</p>
                  <div className="flex flex-col gap-[11px]">
                    {breakdown
                      ? breakdown.map((row) => (
                          <p
                            key={row.age_band}
                            className="text-[16px] leading-[1.45] font-medium text-subtext"
                          >
                            {row.age_band} -{' '}
                            {row.any > 0
                              ? `상관없음 ${row.any}`
                              : `남성 ${row.male} / 여성 ${row.female}`}
                          </p>
                        ))
                      : rows
                          .filter((row) => row.enabled && rowTotal(row) > 0)
                          .map((row) => {
                            const split = splitRow(row)
                            const detail = row.genderAgnostic
                              ? `상관없음 ${split.any}`
                              : `남성 ${split.male} / 여성 ${split.female}`
                            return (
                              <p
                                key={row.id}
                                className="text-[16px] leading-[1.45] font-medium text-subtext"
                              >
                                {row.label} - {detail}
                              </p>
                            )
                          })}
                  </div>
                </div>
              </SummarySection>
            </div>
          </div>

          <aside className="mt-[118px] flex w-[290px] shrink-0 flex-col gap-[30px]">
            <div className="rounded-[22px] border border-line bg-white p-[23px]">
              <p className="text-[14px] leading-[1.45] font-medium text-body">예상 소요</p>
              <p className="mt-[7px] text-[26px] leading-[1.45] font-bold text-heading">
                약 {minutes}분
              </p>
              {/* 실측이 아니라 공식이다. 기준을 같이 적어야 숫자를 믿을 만큼만 믿는다. */}
              <p className="mt-[9px] text-[13px] leading-[1.45] text-placeholder">
                {total}명 × {pageCount}페이지 기준
              </p>
              <hr className="my-[21px] border-line" />
              <p className="text-[13px] leading-[1.45] font-medium text-body">예상 사용량</p>
              <p className="mt-[8px] text-[16px] leading-[1.45] font-bold text-heading">
                약 {formatTokens(tokens)} 토큰
              </p>
              {est && !est.measured ? (
                <p className="mt-[8px] text-[12px] leading-[1.45] text-placeholder">
                  실측 전 추정치예요
                </p>
              ) : null}
            </div>

            <div className="flex items-center gap-[12px] rounded-[18px] border border-divider bg-white p-[19px]">
              <span className="flex size-[39px] shrink-0 items-center justify-center rounded-[12px] bg-[#eaf3ff]">
                <img src={checkMarkBlue} alt="" aria-hidden className="size-[15px]" />
              </span>
              <p className="text-[14px] leading-[1.45] font-medium text-body">
                실행 후에도
                <br />
                중간 결과를 볼 수 있어요.
              </p>
            </div>
          </aside>
        </div>
      </PageBody>
    </AppLayout>
  )
}

function SummarySection({
  title,
  children,
  onEdit,
  last = false,
}: {
  title: string
  children: React.ReactNode
  onEdit?: () => void
  last?: boolean
}) {
  return (
    <section className={`py-[22px] ${last ? '' : 'border-b border-line'}`}>
      <div className="flex items-start justify-between">
        <h2 className="text-[20px] leading-[1.45] font-bold text-heading">{title}</h2>
        {onEdit ? (
          <button
            type="button"
            onClick={onEdit}
            className="text-[14px] leading-[1.45] font-medium text-main hover:underline"
          >
            수정
          </button>
        ) : null}
      </div>
      <div className="mt-[22px]">{children}</div>
    </section>
  )
}
