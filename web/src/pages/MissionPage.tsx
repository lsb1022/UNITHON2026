import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { analyzeMission, getProject, saveMission, type MissionAnalysis } from '../api/client'
import { useMutation, useQuery } from '../api/hooks'
import checkIcon from '../assets/icons/check-filled.svg'
import infoIcon from '../assets/icons/info.svg'
import { AppLayout, PageBody, PageHeading } from '../components/AppLayout'
import { TextAreaField } from '../components/Field'
import { WizardTopBar } from '../components/StepIndicator'
import { WizardFooter } from '../components/WizardFooter'
import { useWizard } from '../state/WizardContext'

const TIPS = [
  '버튼 이름을 직접 알려주기보다 사용자의 목적을 적어요.',
  '한 미션에는 하나의 완료 목표만 넣어요.',
  '실제 상황처럼 맥락을 한 문장 정도 덧붙여도 좋아요.',
]

/**
 * 타이핑이 멎고 이만큼 지나면 분석한다. 글자마다 부르면 서버가 시끄럽다.
 * 분석이 규칙에서 LLM 으로 바뀌면서 한 번 부를 때마다 실제 모델 호출이 나간다 —
 * 문장을 쓰다 잠깐 멈추는 정도로는 부르지 않도록 넉넉히 잡는다.
 */
const DEBOUNCE_MS = 900

export function MissionPage() {
  const { projectId = '' } = useParams()
  const navigate = useNavigate()
  const project = useQuery(() => getProject(projectId), [projectId])
  const save = useMutation(saveMission)
  const { mission, setMission, successCriteria, setSuccessCriteria, testId } = useWizard()

  const [analysis, setAnalysis] = useState<MissionAnalysis | null>(null)
  const [analyzing, setAnalyzing] = useState(false)

  useEffect(() => {
    const text = mission.trim()
    if (text === '') {
      setAnalysis(null)
      setSuccessCriteria('')
      return
    }

    setAnalyzing(true)
    const timer = window.setTimeout(async () => {
      try {
        const result = await analyzeMission(text)
        setAnalysis(result)
        setSuccessCriteria(result.success_criteria ?? '')
      } catch {
        // 분석은 보조 기능이다. 실패해도 미션 작성 자체를 막지 않는다.
        setAnalysis(null)
      } finally {
        setAnalyzing(false)
      }
    }, DEBOUNCE_MS)

    return () => window.clearTimeout(timer)
  }, [mission, setSuccessCriteria])

  const blocked = analysis?.status === 'invalid'

  return (
    <AppLayout
      topBar={
        <WizardTopBar breadcrumb={{ project: project.data?.name ?? '', page: '새 테스트' }} current={2} />
      }
      footer={
        <WizardFooter
          onPrev={() => navigate(`/projects/${projectId}/tests/new`)}
          onNext={async () => {
            if (testId) {
              const saved = await save.run(testId, {
                prompt: mission.trim(),
                success_criteria: successCriteria,
              })
              if (!saved) return
            }
            navigate(`/projects/${projectId}/tests/new/persona`)
          }}
          nextLabel={save.pending ? '저장 중…' : '다음'}
          nextDisabled={save.pending || mission.trim() === '' || blocked}
        />
      }
    >
      <PageBody>
        <div className="max-w-[1240px]">
          <PageHeading
            title="페르소나가 해야 할 일을 알려주세요"
            description="실제 사용자에게 부탁하듯 짧고 구체적으로 적으면 좋아요."
          />

          <div className="mt-[46px]">
            <TextAreaField
              label="미션"
              required
              placeholder="예) 원하는 네일 디자인을 선택하고 견적 요청까지 완료해 주세요."
              value={mission}
              onChange={(event) => setMission(event.target.value)}
              maxLength={200}
              counter
              rows={5}
              className="h-[180px] text-[17px] font-medium"
            />
          </div>

          {analysis && analysis.issues.length > 0 ? (
            <IssueList analysis={analysis} />
          ) : null}

          {save.error ? (
            <p className="mt-[12px] text-[14px] font-medium text-danger">{save.error}</p>
          ) : null}

          <section className="mt-[31px] flex flex-col gap-[9px]">
            <p className="text-[20px] leading-[1.45] font-bold text-heading">성공 기준</p>
            <SuccessCriteria
              criteria={successCriteria}
              status={analysis?.status ?? null}
              analyzing={analyzing}
              empty={mission.trim() === ''}
            />
          </section>

          <section className="mt-[48px] rounded-[20px] border border-line bg-white px-[23px] py-[18px]">
            <p className="flex items-center gap-[6px] text-[16px] leading-[1.45] font-bold text-ink">
              <img src={infoIcon} alt="" aria-hidden className="size-[24px]" />
              좋은 미션은 이렇게 써요
            </p>
            <ul className="mt-[12px] flex flex-col gap-[9px]">
              {TIPS.map((tip) => (
                <li key={tip} className="text-[14px] leading-[1.45] text-subtext">
                  • {tip}
                </li>
              ))}
            </ul>
          </section>
        </div>
      </PageBody>
    </AppLayout>
  )
}

/**
 * 성공 기준 카드.
 *
 * 미션을 쓰기 전에는 초록(=확정)이 아니라 회색이어야 한다. 아무것도 판단하지 않았는데
 * 초록을 보여주면 "이미 검증됐다"고 읽힌다.
 */
function SuccessCriteria({
  criteria,
  status,
  analyzing,
  empty,
}: {
  criteria: string
  status: MissionAnalysis['status'] | null
  analyzing: boolean
  empty: boolean
}) {
  const tone =
    empty || status === null
      ? 'idle'
      : status === 'invalid'
        ? 'danger'
        : status === 'warning'
          ? 'warning'
          : 'ok'

  const shell = {
    idle: 'border-line bg-white',
    ok: 'border-line bg-white',
    warning: 'border-[#ffd52b]/70 bg-[#fffbea]',
    danger: 'border-danger/40 bg-danger-bg/60',
  }[tone]

  const badge = {
    idle: { label: '대기', className: 'bg-track text-subtext' },
    ok: { label: '자동', className: 'bg-success-soft text-success' },
    warning: { label: '확인 필요', className: 'bg-[#fff4cc] text-[#8a6a00]' },
    danger: { label: '수정 필요', className: 'bg-danger-soft text-danger' },
  }[tone]

  return (
    <div className={`flex h-[88px] items-center justify-between rounded-[18px] border px-[23px] ${shell}`}>
      <div className="flex items-center gap-[14px]">
        <span
          className={`flex size-[48px] shrink-0 items-center justify-center rounded-[12px] ${
            tone === 'ok'
              ? 'bg-success-soft'
              : tone === 'danger'
                ? 'bg-danger-soft'
                : tone === 'warning'
                  ? 'bg-[#fff4cc]'
                  : 'bg-track'
          }`}
        >
          {tone === 'ok' ? (
            <img src={checkIcon} alt="" aria-hidden className="size-[24px]" />
          ) : (
            <span
              className={`text-[22px] leading-none font-bold ${
                tone === 'danger' ? 'text-danger' : tone === 'warning' ? 'text-[#8a6a00]' : 'text-subtext'
              }`}
            >
              {tone === 'idle' ? '–' : '!'}
            </span>
          )}
        </span>
        <div className="flex flex-col gap-[6px]">
          <p
            className={`text-[15px] leading-[1.45] font-medium ${
              tone === 'idle' ? 'text-placeholder' : 'text-ink'
            }`}
          >
            {analyzing
              ? '미션을 읽는 중이에요…'
              : (criteria || '미션을 쓰면 성공 기준을 만들어 드려요.')}
          </p>
          <p className="text-[13px] leading-[1.45] text-subtext">
            {tone === 'ok' ? '자동으로 감지해요' : '미션에서 도착점을 찾아 만들어요'}
          </p>
        </div>
      </div>
      <span
        className={`rounded-[15px] px-[20px] py-[5px] text-[13px] leading-[1.45] font-medium ${badge.className}`}
      >
        {badge.label}
      </span>
    </div>
  )
}

function IssueList({ analysis }: { analysis: MissionAnalysis }) {
  const danger = analysis.status === 'invalid'

  return (
    <div
      className={`mt-[16px] rounded-[16px] border px-[20px] py-[16px] ${
        danger ? 'border-danger/40 bg-danger-bg/60' : 'border-[#ffd52b]/70 bg-[#fffbea]'
      }`}
    >
      <p className={`text-[15px] font-bold ${danger ? 'text-danger' : 'text-[#8a6a00]'}`}>
        {danger ? '이대로는 테스트를 돌릴 수 없어요' : '이렇게 고치면 더 정확해져요'}
      </p>
      <ul className="mt-[10px] flex flex-col gap-[10px]">
        {analysis.issues.map((issue) => (
          <li key={issue.kind}>
            <p className="text-[14px] font-medium text-ink">{issue.message}</p>
            <p className="mt-[2px] text-[13px] leading-[1.5] text-body">{issue.fix}</p>
          </li>
        ))}
      </ul>
    </div>
  )
}
