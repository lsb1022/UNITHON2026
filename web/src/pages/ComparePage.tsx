import { useEffect, useState } from 'react'
import {
  compareProjects,
  listComparableProjects,
  type CompareSide,
  type PersonaRow,
} from '../api/client'
import { useQuery } from '../api/hooks'
import { AppLayout, PageBody } from '../components/AppLayout'
import { Chip, Dots, SideResult } from '../components/PersonaBits'
import { ErrorBlock, LoadingBlock } from '../components/StateView'

/**
 * 두 프로젝트 견주기 — 고치기 전과 고친 뒤.
 *
 * 프로젝트 안에서는 주소 하나의 결과만 보여준다. 사용자는 주소를 하나 넣었으니
 * 거기서 다른 사이트가 튀어나오면 안 된다. 대신 **여기서만** 두 프로젝트를 골라
 * 나란히 놓는다.
 *
 * 이 표가 성립하는 이유는 하나다 — 같은 페르소나 열 명을 양쪽에 똑같이 투입했다.
 * 그래서 "P005 가 고치기 전에는 달성했는데 고친 뒤에는 포기했다"가 사이트의 차이지
 * 사람의 차이가 아니라고 말할 수 있다. 사람이 다르면 이 표는 아무 뜻이 없다.
 */
export function ComparePage() {
  const projects = useQuery(() => listComparableProjects(), [])
  const [base, setBase] = useState('')
  const [against, setAgainst] = useState('')

  // 처음 들어오면 앞의 둘을 잡아둔다. 빈 화면부터 보여주면 무엇을 하는 곳인지
  // 알기까지 두 번을 눌러야 한다.
  useEffect(() => {
    const list = projects.data ?? []
    if (list.length >= 2 && !base && !against) {
      setBase(list[0].id)
      setAgainst(list[1].id)
    }
  }, [projects.data, base, against])

  const ready = Boolean(base && against && base !== against)
  const result = useQuery(
    () => (ready ? compareProjects(base, against) : Promise.resolve(null)),
    [base, against, ready],
  )

  const list = projects.data ?? []
  const data = result.data

  return (
    <AppLayout>
      <PageBody>
        <div className="mx-auto w-full max-w-[1402px]">
          <h1 className="text-[34px] leading-[1.45] font-bold text-ink">사이트 비교</h1>
          <p className="mt-[6px] text-[16px] leading-[1.5] text-subtext">
            같은 페르소나를 두 사이트에 똑같이 투입한 결과를 나란히 놓습니다. 고치기 전과 고친
            뒤를 고르면 어떤 사람이 어디서 무너졌는지 보여요.
          </p>

          {projects.loading ? <LoadingBlock label="프로젝트를 불러오는 중이에요" /> : null}
          {projects.error ? (
            <ErrorBlock message={projects.error} onRetry={projects.reload} />
          ) : null}

          {list.length >= 2 ? (
            <div className="mt-[24px] flex flex-wrap items-end gap-[16px]">
              <Picker label="기준 사이트" value={base} options={list} onChange={setBase} />
              <span className="pb-[12px] text-[20px] text-subtext">→</span>
              <Picker label="비교 사이트" value={against} options={list} onChange={setAgainst} />
              <button
                type="button"
                onClick={() => {
                  setBase(against)
                  setAgainst(base)
                }}
                className="h-[46px] rounded-[10px] border border-line px-[16px] text-[14px] font-semibold text-subtext transition-colors hover:text-ink"
              >
                방향 바꾸기
              </button>
            </div>
          ) : null}

          {base && against && base === against ? (
            <p className="mt-[24px] rounded-[12px] bg-bg px-[18px] py-[14px] text-[14px] text-subtext">
              서로 다른 프로젝트 두 개를 골라주세요.
            </p>
          ) : null}

          {result.loading ? <LoadingBlock label="비교하는 중이에요" /> : null}
          {result.error ? <ErrorBlock message={result.error} onRetry={result.reload} /> : null}

          {data && data.ok ? <CompareTable data={data} /> : null}
          {data && !data.ok ? (
            <p className="mt-[24px] rounded-[12px] bg-bg px-[18px] py-[14px] text-[14px] text-subtext">
              {data.message}
            </p>
          ) : null}
        </div>
      </PageBody>
    </AppLayout>
  )
}

function Picker({
  label,
  value,
  options,
  onChange,
}: {
  label: string
  value: string
  options: CompareSide[]
  onChange: (next: string) => void
}) {
  return (
    <label className="flex flex-col gap-[6px]">
      <span className="text-[13px] font-semibold text-subtext">{label}</span>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="h-[46px] min-w-[260px] rounded-[10px] border border-line px-[14px] text-[15px] text-ink"
      >
        {options.map((o) => (
          <option key={o.id} value={o.id}>
            {o.name}
            {o.success_rate === null ? '' : ` · 성공률 ${o.success_rate}%`}
          </option>
        ))}
      </select>
    </label>
  )
}

function CompareTable({
  data,
}: {
  data: {
    base?: CompareSide
    against?: CompareSide
    items: PersonaRow[]
    total?: number
    changed?: number
    exhausted?: number
    axes?: Record<string, string>
  }
}) {
  const items = data.items ?? []
  const axes = data.axes ?? {}
  const axisKeys = Object.keys(axes)
  const changed = data.changed ?? 0

  // 어느 쪽으로 달라졌는지까지 세야 문장을 쓸 수 있다. "3명이 달라졌다"만으로는
  // 좋아진 건지 나빠진 건지 알 수 없다.
  const worse = items.filter(
    (p) => p.changed && p.baseline?.outcome === 'success' && p.compare?.outcome !== 'success',
  ).length
  const better = changed - worse

  const baseName = data.base?.name ?? '기준 사이트'
  const againstName = data.against?.name ?? '비교 사이트'

  return (
    <section className="mt-[28px]">
      <div className="flex flex-wrap items-center gap-[8px]">
        <Chip tone="plain">전체 {data.total ?? items.length}명</Chip>
        {changed > 0 ? <Chip tone="warn">결과가 달라진 {changed}명</Chip> : null}
        {(data.exhausted ?? 0) > 0 ? <Chip tone="hold">스텝 소진 {data.exhausted}명</Chip> : null}
        <span className="ml-auto text-[13px] text-subtext tabular-nums">
          {baseName} {pct(data.base?.success_rate)} → {againstName} {pct(data.against?.success_rate)}
        </span>
      </div>

      <div className="mt-[12px] rounded-[12px] bg-bg px-[18px] py-[14px]">
        <p className="text-[15px] font-semibold text-ink">
          {changed === 0
            ? `두 사이트에서 열 명의 결과가 모두 같았어요.`
            : `${worse > 0 ? `${worse}명이 ${baseName}에서는 달성했지만 ${againstName}에서는 못 했어요.` : ''}${
                better > 0
                  ? `${worse > 0 ? ' ' : ''}${better}명은 반대로 ${againstName}에서 해냈어요.`
                  : ''
              }`}
        </p>
        <p className="mt-[4px] text-[13px] text-subtext">
          {axisKeys.map((k) => axes[k]).join('·')}는 테스트 중 AI가 내부적으로 생성한 행동
          특성이며, 사용자가 직접 설정하는 값이 아니에요. 두 사이트에 같은 사람을 투입했기
          때문에 이 차이는 사람이 아니라 화면에서 온 것입니다.
        </p>
      </div>

      <div className="mt-[14px] overflow-x-auto rounded-[16px] border border-line">
        <table className="w-full min-w-[980px] border-collapse text-left">
          <thead>
            <tr className="bg-bg text-[13px] text-subtext">
              <th className="px-[18px] py-[12px] font-medium">페르소나</th>
              {axisKeys.map((k) => (
                <th key={k} className="px-[10px] py-[12px] font-medium whitespace-nowrap">
                  {axes[k]}
                </th>
              ))}
              <th className="px-[14px] py-[12px] font-medium whitespace-nowrap">{baseName}</th>
              <th className="px-[14px] py-[12px] font-medium whitespace-nowrap">{againstName}</th>
            </tr>
          </thead>
          <tbody>
            {items.map((persona) => (
              <tr
                key={persona.id}
                className={`border-t border-line text-[14px] ${
                  persona.changed ? 'bg-[#fff6f5]' : ''
                }`}
              >
                <td className="px-[18px] py-[12px]">
                  <p className="font-semibold text-ink">{persona.code}</p>
                  <p className="text-[12px] text-subtext">{persona.name}</p>
                </td>
                {axisKeys.map((k) => (
                  <td key={k} className="px-[10px] py-[12px]">
                    <Dots value={persona.traits?.[k] ?? 0} />
                  </td>
                ))}
                <td className="px-[14px] py-[12px]">
                  <SideResult side={persona.baseline ?? null} />
                </td>
                <td className="px-[14px] py-[12px]">
                  <div className="flex items-center gap-[8px]">
                    <SideResult side={persona.compare ?? null} />
                    {persona.changed ? <Chip tone="warn">결과 변화</Chip> : null}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  )
}

function pct(value: number | null | undefined): string {
  return value === null || value === undefined ? '–' : `${value}%`
}
