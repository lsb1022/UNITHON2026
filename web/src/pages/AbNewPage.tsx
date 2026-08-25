import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  createAbTest,
  createProject,
  listProjects,
  listTests,
  type ProjectCard,
  type TestStats,
} from '../api/client'
import { useMutation, useQuery } from '../api/hooks'
import checkMark from '../assets/icons/check-mark.svg'
import apkIcon from '../assets/img/src-apk.png'
import githubIcon from '../assets/img/src-github.png'
import linkIcon from '../assets/img/src-link.png'
import { AppLayout, PageBody, PageHeading } from '../components/AppLayout'
import { CATEGORIES, CategorySelect } from '../components/CategorySelect'
import { ConnectionCard } from '../components/ConnectionCard'
import { DEVICE_PRESETS, DeviceSelect } from '../components/DeviceSelect'
import { Emoji } from '../components/Emoji'
import { FieldLabel, TextField } from '../components/Field'
import { PreviewModal } from '../components/PreviewModal'
import { SegmentedControl } from '../components/SegmentedControl'
import { SitePreview } from '../components/SitePreview'
import { AB_STEPS, WizardTopBar, type WizardStep } from '../components/StepIndicator'
import { ErrorBlock, LoadingBlock } from '../components/StateView'
import { WizardFooter } from '../components/WizardFooter'
import { useConnection } from '../hooks/useConnection'
import { timeAgo } from '../lib/time'

const SOURCES = [
  { value: 'web', label: '웹 링크', icon: <img src={linkIcon} alt="" className="size-[14px]" /> },
  { value: 'github', label: '깃허브', icon: <img src={githubIcon} alt="" className="size-[19px]" /> },
  { value: 'apk', label: 'APK 파일', icon: <img src={apkIcon} alt="" className="size-[19px]" /> },
] as const

/**
 * 새 A/B 테스트 (Figma 329:24648 · 329:25865 · 334:26632 · 334:27760).
 *
 * 네 걸음을 한 화면 안에서 걷는다. 주소를 나누면 뒤로가기로 2단계에 들어왔을 때
 * 1단계에서 고른 프로젝트가 비어 있는 상태가 생긴다 — 그러면 "미션 선택"이
 * 무엇의 미션인지 말할 수 없다.
 */
export function AbNewPage() {
  const navigate = useNavigate()
  const [step, setStep] = useState<WizardStep>(1)

  // 1단계: 개선 전 프로젝트 A
  const [projectA, setProjectA] = useState<ProjectCard | null>(null)
  // 2단계: 그 프로젝트에서 견줄 테스트(미션)
  const [testA, setTestA] = useState<TestStats | null>(null)
  // 3단계: 개선 후 프로젝트 B
  const [abName, setAbName] = useState('')
  const [bName, setBName] = useState('')
  const [source, setSource] = useState<(typeof SOURCES)[number]['value']>('web')
  const [device, setDevice] = useState(DEVICE_PRESETS[3].id)
  const [category, setCategory] = useState<string>(CATEGORIES[0])
  const [link, setLink] = useState('')
  const [previewOpen, setPreviewOpen] = useState(false)
  const [abId, setAbId] = useState<string | null>(null)

  const connection = useConnection()
  const makeProject = useMutation(createProject)
  const makeAb = useMutation(createAbTest)

  const back = () => (step === 1 ? navigate('/ab') : setStep((s) => (s - 1) as WizardStep))

  const nextDisabled =
    (step === 1 && !projectA) ||
    (step === 2 && !testA) ||
    (step === 3 &&
      (makeProject.pending ||
        abName.trim() === '' ||
        bName.trim() === '' ||
        link.trim() === '' ||
        !connection.connected))

  const goNext = async () => {
    if (step === 3) {
      // B 는 아직 없는 프로젝트다. 먼저 만들어야 비교할 대상이 생긴다.
      const created = await makeProject.run({
        name: bName.trim(),
        category: category.trim(),
        target_url: connection.previewUrl ?? link,
        source,
        device_preset: device,
        preview_embeddable: connection.embeddable,
      })
      if (!created || !projectA) return
      const made = await makeAb.run({
        name: abName.trim(),
        a_project_id: projectA.id,
        b_project_id: created.id,
      })
      if (!made?.id) return
      setAbId(made.id)
      setStep(4)
      return
    }
    setStep((s) => (s + 1) as WizardStep)
  }

  // 4단계는 결과가 나올 때까지 기다리는 화면이라 아래 버튼이 없다.
  if (step === 4 && abId) {
    return (
      <AnalyzingStep
        abId={abId}
        aName={projectA?.name ?? ''}
        aUrl={projectA?.preview_url ?? null}
        bName={bName}
        bUrl={connection.previewUrl ?? link}
      />
    )
  }

  return (
    <AppLayout
      topBar={
        <WizardTopBar breadcrumb={{ project: 'A/B 테스트', page: '새 테스트' }} current={step} steps={AB_STEPS} />
      }
      footer={
        <WizardFooter
          onPrev={back}
          onNext={goNext}
          nextLabel={makeProject.pending || makeAb.pending ? '만드는 중…' : '다음으로'}
          nextDisabled={nextDisabled}
        />
      }
    >
      <PageBody>
        {step === 1 ? (
          <PickProject
            picked={projectA}
            onPick={(project) => {
              // 프로젝트를 바꾸면 앞서 고른 테스트는 남의 것이 된다. 여기서 비운다.
              if (project.id !== projectA?.id) setTestA(null)
              setProjectA(project)
            }}
          />
        ) : null}
        {step === 2 && projectA ? (
          <PickTest project={projectA} picked={testA} onPick={setTestA} />
        ) : null}
        {step === 3 ? (
          <div className="max-w-[1280px]">
            <PageHeading
              title="개선후 프로젝트 B를 입력해주세요"
              description="이전에 입력한 프로젝트A 와 비교할 B를 입력해야해요!"
            />

            <SegmentedControl
              options={SOURCES}
              value={source}
              onChange={setSource}
              className="mt-[21px] w-[420px]"
            />

            <div className="mt-[17px] flex flex-col gap-[20px]">
              <TextField
                label="A/B 테스트 이름 입력"
                required
                placeholder="예) 쇼핑몰 2가지 버전 결제 과정 테스트"
                value={abName}
                onChange={(event) => setAbName(event.target.value)}
                maxLength={100}
                counter
              />

              <TextField
                label="개선후 프로젝트 B 이름 입력"
                required
                placeholder="예) 쇼핑몰 v.2"
                value={bName}
                onChange={(event) => setBName(event.target.value)}
                maxLength={100}
                counter
              />

              <div className="flex flex-col gap-[7px]">
                <FieldLabel required>실행 환경 디바이스</FieldLabel>
                <DeviceSelect value={device} onChange={setDevice} />
              </div>

              <div className="flex flex-col gap-[7px]">
                <FieldLabel required>프로젝트 카테고리</FieldLabel>
                <CategorySelect value={category} onChange={setCategory} />
              </div>

              <TextField
                label="프로젝트 링크"
                required
                placeholder="www.example.com/proto/..."
                value={link}
                onChange={(event) => {
                  setLink(event.target.value)
                  connection.reset()
                }}
                onKeyDown={(event) => {
                  if (event.key === 'Enter') connection.run(link)
                }}
                leading={<span className="shrink-0 text-[15px] text-placeholder">https://</span>}
                trailing={
                  <button
                    type="button"
                    onClick={() => connection.run(link)}
                    disabled={link.trim() === '' || connection.state.status === 'checking'}
                    className="h-[62px] w-[160px] shrink-0 rounded-[14px] bg-main text-[20px] leading-[1.45] font-bold text-white transition-colors hover:bg-[#2872dd] disabled:cursor-not-allowed disabled:bg-[#c4d9f9]"
                  >
                    {connection.state.status === 'checking' ? '확인 중…' : '연결하기'}
                  </button>
                }
              />

              <ConnectionCard
                state={connection.state}
                onPreview={() => setPreviewOpen(true)}
                onRetry={() => connection.run(link)}
              />

              {makeProject.error ? (
                <p className="text-[14px] font-medium text-danger">{makeProject.error}</p>
              ) : null}
              {makeAb.error ? (
                <p className="text-[14px] font-medium text-danger">{makeAb.error}</p>
              ) : null}
            </div>
          </div>
        ) : null}
      </PageBody>

      <PreviewModal
        open={previewOpen}
        onClose={() => setPreviewOpen(false)}
        url={connection.previewUrl}
        embeddable={connection.embeddable}
        blockReason={connection.blockReason}
      />
    </AppLayout>
  )
}

// --------------------------------------------------------------------------- //
// 1단계 — 개선 전 프로젝트 A
// --------------------------------------------------------------------------- //

function PickProject({
  picked,
  onPick,
}: {
  picked: ProjectCard | null
  onPick: (project: ProjectCard) => void
}) {
  const projects = useQuery(listProjects, [])

  return (
    <div className="mx-auto w-full max-w-[1442px]">
      <PageHeading
        title="개선전 URL이 첨부된 프로젝트를 선택해주세요"
        description="개선전 프로젝트는 A로 해당이 됩니다"
      />

      <p className="mt-[24px] rounded-[10px] bg-brand-soft px-[18px] py-[12px] text-[13px] font-medium text-main">
        비교 정확도를 높이려면 같은 목적의 프로젝트를 선택해주세요
      </p>

      <h2 className="mt-[30px] text-[16px] font-semibold text-ink">최근 프로젝트</h2>

      {projects.loading ? <LoadingBlock label="프로젝트를 불러오는 중이에요" /> : null}
      {projects.error ? <ErrorBlock message={projects.error} onRetry={projects.reload} /> : null}

      <div className="mt-[16px] grid grid-cols-3 gap-x-[31px] gap-y-[22px]">
        {(projects.data ?? []).map((project) => {
          const active = picked?.id === project.id
          return (
            <button
              key={project.id}
              type="button"
              onClick={() => onPick(project)}
              className={`relative flex h-[288px] flex-col gap-[8px] rounded-[16px] bg-white p-[14px] text-left transition-shadow hover:shadow-[0_6px_20px_rgba(0,0,0,0.06)] ${
                active ? 'border-2 border-main' : 'border border-line'
              }`}
            >
              {active ? (
                <span className="absolute top-[24px] right-[24px] z-10 grid size-[26px] place-items-center rounded-full bg-main">
                  <img src={checkMark} alt="" className="size-[13px]" />
                </span>
              ) : null}
              <div className="min-h-0 flex-1 overflow-hidden rounded-[12px] border border-line">
                <SitePreview url={project.preview_url} alt={`${project.name} 미리보기`} />
              </div>
              <div className="px-[8px]">
                <p className="text-[20px] leading-[1.45] font-bold text-ink">{project.name}</p>
                <p className="mt-[8px] text-[14px] text-subtext">
                  진행한 테스트 {project.test_count}개
                </p>
                <p className="mt-[6px] text-[14px] text-subtext">
                  {timeAgo(project.last_activity_at)}
                </p>
              </div>
            </button>
          )
        })}
      </div>
    </div>
  )
}

// --------------------------------------------------------------------------- //
// 2단계 — 견줄 테스트(미션)
// --------------------------------------------------------------------------- //

function PickTest({
  project,
  picked,
  onPick,
}: {
  project: ProjectCard
  picked: TestStats | null
  onPick: (test: TestStats) => void
}) {
  const tests = useQuery(() => listTests(project.id), [project.id])
  const list = tests.data ?? []

  return (
    <div className="mx-auto w-full max-w-[1442px]">
      <PageHeading
        title={`${project.name} 프로젝트에서 하나의 테스트를 선택해주세요`}
        description="동일한 미션과 동일한 페르소나여야 더 정확한 A/B 테스트가 가능합니다"
      />

      {tests.loading ? <LoadingBlock label="테스트를 불러오는 중이에요" /> : null}
      {tests.error ? <ErrorBlock message={tests.error} onRetry={tests.reload} /> : null}
      {!tests.loading && !tests.error && list.length === 0 ? (
        <p className="py-[80px] text-center text-[15px] text-subtext">
          이 프로젝트에는 아직 진행한 테스트가 없어요. 다른 프로젝트를 골라 주세요.
        </p>
      ) : null}

      <div className="mt-[36px] flex flex-col gap-[15px]">
        {list.map((test) => {
          const active = picked?.test_id === test.test_id
          return (
            <button
              key={test.test_id}
              type="button"
              onClick={() => onPick(test)}
              className={`relative flex w-full items-center justify-between rounded-[14px] bg-white px-[30px] py-[20px] text-left transition-shadow hover:shadow-[0_6px_20px_rgba(0,0,0,0.06)] ${
                active ? 'border-2 border-main' : 'border border-line'
              }`}
            >
              <div className="flex min-w-0 flex-1 items-center gap-[15px]">
                <div className="h-[70px] w-[70px] shrink-0 overflow-hidden rounded-[10px] border border-line">
                  <SitePreview url={project.preview_url} alt="" fit="cover" />
                </div>
                <div className="min-w-0">
                  <p className="text-[20px] leading-[1.45] font-bold text-ink">{test.name}</p>
                  <p className="mt-[7px] text-[14px] text-subtext">
                    페르소나 {test.persona_count}명
                  </p>
                  <p className="mt-[5px] text-[14px] text-subtext">{timeAgo(test.created_at)}</p>
                </div>
              </div>

              <div className="flex shrink-0 items-center gap-[12px]">
                <Metric icon="target" label="성공률" value={test.success_rate} />
                <Metric icon="warning" label="이탈률" value={test.drop_rate} />
                {active ? (
                  <span className="grid size-[26px] place-items-center rounded-full bg-main">
                    <img src={checkMark} alt="" className="size-[13px]" />
                  </span>
                ) : (
                  <span className="size-[26px]" />
                )}
              </div>
            </button>
          )
        })}
      </div>
    </div>
  )
}

function Metric({
  icon,
  label,
  value,
}: {
  icon: 'target' | 'warning'
  label: string
  value: number | null
}) {
  return (
    <span className="flex items-center gap-[5px]">
      <Emoji name={icon} size={26} />
      <span className="text-[17px] text-ink">{label}</span>
      <span className="w-[64px] text-[17px] font-semibold text-ink tabular-nums">
        {value === null ? '–' : `${value}%`}
      </span>
    </span>
  )
}

// --------------------------------------------------------------------------- //
// 4단계 — 비교 분석 중
// --------------------------------------------------------------------------- //

const PHASES = ['페르소나 매칭', '행동 로그 정렬', '결과 차이 분석', '사이트별 다이어그램 생성']
const TICK_MS = 90

function AnalyzingStep({
  abId,
  aName,
  aUrl,
  bName,
  bUrl,
}: {
  abId: string
  aName: string
  aUrl: string | null
  bName: string
  bUrl: string | null
}) {
  const navigate = useNavigate()
  const [percent, setPercent] = useState(0)

  // 비교 자체는 이미 끝나 있다(같은 실행 기록을 맞춰 보는 일이다). 여기서 기다리는
  // 것은 사람이 무슨 일이 일어났는지 읽을 시간이다 — 그래서 진행률은 화면의 것이다.
  useEffect(() => {
    const timer = window.setInterval(() => {
      setPercent((value) => {
        if (value >= 100) {
          window.clearInterval(timer)
          navigate(`/ab/${abId}`, { replace: true })
          return 100
        }
        return value + 2
      })
    }, TICK_MS)
    return () => window.clearInterval(timer)
  }, [abId, navigate])

  // 네 단계를 진행률에 고르게 나눠 준다.
  const activeIndex = Math.min(PHASES.length - 1, Math.floor(percent / (100 / PHASES.length)))

  return (
    <AppLayout
      topBar={
        <WizardTopBar breadcrumb={{ project: 'A/B 테스트', page: '새 테스트' }} current={4} steps={AB_STEPS} />
      }
    >
      <PageBody>
        <div className="mx-auto w-full max-w-[1000px] pt-[80px] text-center">
          <h1 className="text-[30px] leading-[1.4] font-bold text-heading">
            A/B 테스트를 비교 분석하고 있어요
          </h1>
          <p className="mt-[14px] text-[14px] text-muted">
            두 프로젝트에서 같은 페르소나의 행동을 맞춰 보고 결과 차이를 정리하고 있어요.
          </p>

          <section className="mt-[46px] rounded-[16px] bg-bg px-[40px] pt-[36px] pb-[40px] text-left">
            <div className="flex items-center justify-center gap-[26px]">
              <Side tag="A" name={aName} url={aUrl} />
              <span className="text-[13px] font-bold text-subtext">VS</span>
              <Side tag="B" name={bName} url={bUrl} />
            </div>

            <div className="mt-[42px] flex items-center gap-[16px]">
              <span className="w-[80px] shrink-0 text-[13px] font-medium text-heading">
                분석 진행률
              </span>
              <span className="h-[8px] min-w-0 flex-1 rounded-full bg-white">
                <span
                  className="block h-full rounded-full bg-main transition-[width] duration-100"
                  style={{ width: `${percent}%` }}
                />
              </span>
              <span className="w-[40px] shrink-0 text-right text-[13px] font-semibold text-main tabular-nums">
                {percent}%
              </span>
            </div>

            <ul className="mt-[34px] flex flex-col gap-[18px]">
              {PHASES.map((phase, index) => {
                const done = index < activeIndex || percent >= 100
                const running = index === activeIndex && percent < 100
                return (
                  <li key={phase} className="flex items-center gap-[14px]">
                    <span
                      className={`grid size-[20px] shrink-0 place-items-center rounded-full ${
                        done || running ? 'bg-main' : 'bg-line'
                      }`}
                    >
                      <img src={checkMark} alt="" className="size-[10px]" />
                    </span>
                    <span
                      className={`flex-1 text-[13px] ${running ? 'font-bold text-heading' : 'text-body'}`}
                    >
                      {phase}
                      {running ? (
                        <span className="ml-[12px] text-[12px] font-normal text-muted">
                          잠시만 기다려주세요. 분석이 끝나면 비교 결과 화면으로 이동합니다.
                        </span>
                      ) : null}
                    </span>
                    <span
                      className={`shrink-0 text-[12px] ${running ? 'text-main' : 'text-subtext'}`}
                    >
                      {done ? '완료' : running ? '진행 중' : '대기'}
                    </span>
                  </li>
                )
              })}
            </ul>
          </section>
        </div>
      </PageBody>
    </AppLayout>
  )
}

function Side({ tag, name, url }: { tag: 'A' | 'B'; name: string; url: string | null }) {
  return (
    <div className="w-[290px] overflow-hidden rounded-[12px] border border-line bg-white">
      <div className="flex items-center gap-[7px] px-[12px] py-[9px]">
        <span className="text-[16px] font-bold text-main">{tag}</span>
        <span className="truncate text-[13px] font-medium text-ink">{name}</span>
      </div>
      <div className="h-[110px] border-t border-line">
        <SitePreview url={url} alt="" />
      </div>
    </div>
  )
}
