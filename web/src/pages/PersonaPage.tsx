import type { ReactNode } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { getProject, savePersonaSpecs } from '../api/client'
import { useMutation, useQuery } from '../api/hooks'
import checkMark from '../assets/icons/check-mark.svg'
import infoIcon from '../assets/icons/info.svg'
import { AppLayout, PageBody } from '../components/AppLayout'
import {
  AgnosticNotice,
  AgnosticToggle,
  GenderRatioSlider,
} from '../components/GenderRatioSlider'
import { WizardTopBar } from '../components/StepIndicator'
import { WizardFooter } from '../components/WizardFooter'
import { estimateRun, formatTokens } from '../lib/estimate'
import { splitRow, useWizard, type AgeRow } from '../state/WizardContext'

export function PersonaPage() {
  const { projectId = '' } = useParams()
  const navigate = useNavigate()
  const project = useQuery(() => getProject(projectId), [projectId])
  const save = useMutation(savePersonaSpecs)
  const { testName, testId, rows, setRows, totalPersonas, countByGender } = useWizard()

  const estimate = estimateRun(totalPersonas)

  const patch = (id: string, next: Partial<AgeRow>) =>
    setRows((prev) => prev.map((row) => (row.id === id ? { ...row, ...next } : row)))

  return (
    <AppLayout
      topBar={
        <WizardTopBar breadcrumb={{ project: project.data?.name ?? '', page: testName }} current={3} />
      }
      footer={
        <WizardFooter
          onPrev={() => navigate(`/projects/${projectId}/tests/new/mission`)}
          onNext={async () => {
            if (testId) {
              const saved = await save.run(
                testId,
                rows.map((row) => ({
                  age_band: row.id,
                  total: row.enabled ? row.total : 0,
                  female_percent: row.femalePercent,
                  gender_agnostic: row.genderAgnostic,
                  enabled: row.enabled,
                })),
              )
              if (!saved) return
            }
            navigate(`/projects/${projectId}/tests/new/review`)
          }}
          nextLabel={save.pending ? '저장 중…' : '다음'}
          nextDisabled={save.pending || totalPersonas === 0}
        />
      }
    >
      <PageBody>
        <div className="flex gap-[30px]">
          <div className="min-w-0 max-w-[1240px] flex-1">
            <header className="flex flex-col gap-[4px]">
              <h1 className="text-[34px] font-bold text-heading">어떤 사용자를 테스트할까요?</h1>
              <p className="text-[16px] text-subtext">
                연령대별 총 인원을 입력한 뒤, 슬라이더로 여성·남성 비율만 조정해 주세요.
              </p>
            </header>

            <section className="mt-[29px] flex h-[92px] items-center justify-between rounded-[18px] border border-line bg-white px-[24px]">
              <div className="flex flex-col gap-[4px]">
                <p className="font-noto text-[14px] font-medium text-subtext">총 테스트 인원</p>
                <p className="font-noto text-[24px] font-bold text-heading">{totalPersonas}명</p>
              </div>
              <div className="flex items-center gap-[10px]">
                <Chip className="bg-[#eaf2ff] text-main">남성 {countByGender('male')}명</Chip>
                <Chip className="bg-[#f2eeff] text-[#6b5ce7]">
                  여성 {countByGender('female')}명
                </Chip>
                <Chip className="bg-track text-body">상관없음 {countByGender('any')}명</Chip>
              </div>
            </section>

            <section className="mt-[18px] overflow-hidden rounded-[18px] border border-line bg-white px-[24px]">
              {/* 폭이 좁아져도 열이 무너지지 않도록 고정폭은 최소한만 두고 나머지를 비율로 준다. */}
              <div className="flex h-[56px] items-center gap-[16px] font-noto text-[13px] font-medium text-subtext">
                <span className="w-[150px] shrink-0">연령대</span>
                <span className="w-[152px] shrink-0">총 인원</span>
                <span className="min-w-[240px] flex-1">성별 비율</span>
                <span className="w-[104px] shrink-0 text-center">옵션</span>
              </div>

              {rows.map((row) => (
                <AgeRowItem key={row.id} row={row} onPatch={(next) => patch(row.id, next)} />
              ))}
            </section>

            {save.error ? (
              <p className="mt-[16px] text-[14px] font-medium text-danger">{save.error}</p>
            ) : null}

            <div className="mt-[20px] flex h-[58px] items-center gap-[12px] rounded-[16px] bg-[#eaf2ff] px-[18px]">
              <img src={infoIcon} alt="" aria-hidden className="size-[28px]" />
              <p className="font-noto text-[13px] text-subtext">
                슬라이더를 왼쪽으로 옮길수록 여성 비율이, 오른쪽으로 옮길수록 남성 비율이 높아져요.
                상관없음을 선택하면 비율을 자동으로 배정해요.
              </p>
            </div>
          </div>

          <aside className="mt-[100px] h-[696px] w-[225px] shrink-0 rounded-[22px] border border-line bg-white px-[24px] pt-[64px]">
            <p className="text-[14px] leading-[1.45] font-medium text-body">예상 토큰 사용량</p>
            <p className="mt-[5px] text-[26px] leading-[1.45] font-bold text-heading">
              약 {formatTokens(estimate.tokens)}
            </p>
            <p className="mt-[16px] text-[13px] leading-[1.45] text-placeholder">
              {totalPersonas}명 × {estimate.pageCount}페이지 기준
            </p>
            <p className="mt-[4px] text-[13px] leading-[1.45] text-placeholder">
              예상 소요 약 {estimate.minutes}분
            </p>
          </aside>
        </div>
      </PageBody>
    </AppLayout>
  )
}

function AgeRowItem({ row, onPatch }: { row: AgeRow; onPatch: (next: Partial<AgeRow>) => void }) {
  const split = splitRow(row)

  return (
    <div
      className={`flex h-[78px] items-center gap-[16px] border-t border-line ${
        row.enabled ? '' : 'opacity-45'
      }`}
    >
      <div className="flex w-[150px] shrink-0 items-center gap-[14px]">
        <button
          type="button"
          role="checkbox"
          aria-checked={row.enabled}
          aria-label={`${row.label} 포함`}
          onClick={() => onPatch({ enabled: !row.enabled, ...(row.enabled ? { total: 0 } : {}) })}
          className={`grid size-[26px] place-items-center rounded-[8px] ${
            row.enabled ? 'bg-main' : 'border border-line'
          }`}
        >
          {row.enabled ? (
            <img src={checkMark} alt="" aria-hidden className="size-[15px]" />
          ) : null}
        </button>
        <span className="font-noto text-[16px] font-bold text-heading">{row.label}</span>
      </div>

      <div className="w-[152px] shrink-0">
        <div
          className={`flex h-[46px] w-full items-center rounded-[12px] border px-[15px] ${
            row.enabled ? 'border-line bg-white' : 'border-transparent bg-track'
          }`}
        >
          <input
            type="number"
            min={0}
            disabled={!row.enabled}
            aria-label={`${row.label} 총 인원`}
            value={row.total}
            onChange={(event) => onPatch({ total: Math.max(0, Number(event.target.value) || 0) })}
            className="w-full min-w-0 bg-transparent font-noto text-[16px] font-bold text-heading outline-none [appearance:textfield] disabled:text-subtext [&::-webkit-inner-spin-button]:appearance-none [&::-webkit-outer-spin-button]:appearance-none"
          />
          <span className="shrink-0 font-noto text-[13px] text-subtext">명</span>
        </div>
      </div>

      {/* 상관없음이면 슬라이더를 흐리고 그 위에 안내 pill 을 얹는다 (Figma 130:13987) */}
      <div className="relative flex min-w-[240px] flex-1 items-center">
        <GenderRatioSlider
          femalePercent={row.femalePercent}
          onChange={(value) => onPatch({ femalePercent: value })}
          disabled={!row.enabled || row.genderAgnostic}
          label={`${row.label} 여성 비율`}
        />
        {row.genderAgnostic && row.enabled ? (
          <span className="absolute inset-0 flex items-center justify-center">
            <AgnosticNotice />
          </span>
        ) : null}
      </div>

      <div className="flex w-[104px] shrink-0 justify-center">
        <AgnosticToggle
          active={row.genderAgnostic}
          disabled={!row.enabled}
          onToggle={() => onPatch({ genderAgnostic: !row.genderAgnostic })}
          label={`${row.label} 성별 상관없음`}
        />
      </div>

      <span className="sr-only">
        남성 {split.male}명, 여성 {split.female}명, 상관없음 {split.any}명
      </span>
    </div>
  )
}

function Chip({ children, className }: { children: ReactNode; className: string }) {
  return (
    <span
      className={`flex h-[34px] items-center justify-center rounded-[17px] px-[16px] font-noto text-[13px] font-medium whitespace-nowrap ${className}`}
    >
      {children}
    </span>
  )
}
