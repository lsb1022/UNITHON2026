import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { getTestPersonas, listTests, type PersonaRow, type TestStats } from '../api/client'
import { useQuery } from '../api/hooks'
import chevronDownIcon from '../assets/icons/chevron-down.svg'
import avatar from '../assets/img/avatar.png'
import { Icon, type IconName } from './Icon'

type TabValue = 'test' | 'persona'

const TABS: { value: TabValue; label: string; icon: IconName }[] = [
  { value: 'test', label: '테스트', icon: 'paper' },
  { value: 'persona', label: '페르소나', icon: 'personaTab' },
]

/**
 * 테스트 상세의 왼쪽 목록 (Figma 264:8035 / 264:8738).
 *
 * 전역 사이드바(프로젝트·팀·크레딧·설정)를 대신한다 — 이 화면에서는 상단 바가
 * 화면 전체 폭을 쓰고, 왼쪽에는 같은 프로젝트의 테스트 목록이 온다.
 */
export function TestSidebar({
  projectId,
  testId,
  personaTotal,
}: {
  projectId: string
  testId: string
  personaTotal: number
}) {
  const [tab, setTab] = useState<TabValue>('test')

  return (
    <aside className="flex w-[248px] shrink-0 flex-col border-r border-line bg-white">
      <div className="flex shrink-0 pt-[22px]">
        {TABS.map((item) => {
          const active = item.value === tab
          return (
            <button
              key={item.value}
              type="button"
              role="tab"
              aria-selected={active}
              onClick={() => setTab(item.value)}
              className="flex flex-1 flex-col gap-[9px]"
            >
              <span
                className={`flex items-center justify-center gap-[4px] text-[16px] transition-colors ${
                  active ? 'text-main' : 'text-subtext hover:text-ink'
                }`}
              >
                <Icon name={item.icon} size={item.value === 'test' ? 16 : 19} />
                {item.label}
              </span>
              <span className={`h-[2px] w-full ${active ? 'bg-main' : 'bg-line'}`} />
            </button>
          )
        })}
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto">
        {tab === 'test' ? (
          <TestList projectId={projectId} testId={testId} />
        ) : (
          <PersonaList testId={testId} fallbackTotal={personaTotal} />
        )}
      </div>

      {/* 프로필 블록 위에는 구분선이 없다 (전역 사이드바와 같은 규칙). */}
      <div className="flex h-[70px] shrink-0 items-center px-[30px]">
        <button type="button" className="flex items-center gap-[7px]">
          <img src={avatar} alt="" className="size-[35px] rounded-full object-cover" />
          <span className="text-[20px] text-ink">영찬</span>
          <span className="text-[13px] leading-[1.45] font-medium text-subtext">Pro</span>
          <img src={chevronDownIcon} alt="" className="size-[24px]" />
        </button>
      </div>
    </aside>
  )
}

function TestList({ projectId, testId }: { projectId: string; testId: string }) {
  const navigate = useNavigate()
  const tests = useQuery(() => listTests(projectId), [projectId])

  if (tests.loading) return <SidebarNote>불러오는 중이에요</SidebarNote>
  if (tests.error) return <SidebarNote>{tests.error}</SidebarNote>

  return (
    <ul className="mt-[14px] flex flex-col">
      {(tests.data ?? []).map((test: TestStats) => (
        <li key={test.test_id}>
          <SidebarRow
            icon="folder"
            label={test.name}
            active={test.test_id === testId}
            onClick={() => navigate(`/projects/${projectId}/tests/${test.test_id}`)}
          />
        </li>
      ))}
    </ul>
  )
}

function PersonaList({ testId, fallbackTotal }: { testId: string; fallbackTotal: number }) {
  const personas = useQuery(() => getTestPersonas(testId), [testId])

  if (personas.loading) return <SidebarNote>불러오는 중이에요</SidebarNote>
  if (personas.error) return <SidebarNote>{personas.error}</SidebarNote>

  const total = personas.data?.total ?? fallbackTotal
  const items = personas.data?.items ?? []

  return (
    <>
      <p className="pt-[13px] text-center text-[12px] leading-[1.45] text-subtext">총 {total}명</p>
      {items.length === 0 ? (
        <SidebarNote>아직 만들어진 페르소나가 없어요</SidebarNote>
      ) : (
        <ul className="mt-[15px] flex flex-col">
          {items.map((persona: PersonaRow) => (
            <li key={persona.id}>
              <SidebarRow icon="userProfile" label={persona.name} title={personaTitle(persona)} />
            </li>
          ))}
        </ul>
      )}
    </>
  )
}

/** 목록은 이름만 보여준다. 나머지는 마우스를 올렸을 때 알려준다. */
function personaTitle(persona: PersonaRow): string {
  const result =
    persona.outcome === 'success' ? '성공' : persona.outcome === 'drop' ? '이탈' : '기록 없음'
  return `${persona.name} · ${persona.age_band} ${persona.gender} · ${result}`
}

function SidebarRow({
  icon,
  label,
  title,
  active = false,
  onClick,
}: {
  icon: IconName
  label: string
  title?: string
  active?: boolean
  onClick?: () => void
}) {
  return (
    <div className="flex h-[55px] items-center px-[15px]">
      <button
        type="button"
        onClick={onClick}
        title={title ?? label}
        disabled={!onClick}
        className={`flex h-[49px] min-w-0 flex-1 items-center gap-[12px] rounded-[16px] px-[15px] text-left transition-colors ${
          active
            ? 'bg-main-soft text-main'
            : `text-subtext ${onClick ? 'hover:bg-black/[0.03]' : 'cursor-default'}`
        }`}
      >
        <Icon name={icon} />
        <span className="min-w-0 flex-1 truncate text-[15px] leading-[1.45] font-semibold">
          {label}
        </span>
      </button>
    </div>
  )
}

function SidebarNote({ children }: { children: React.ReactNode }) {
  return <p className="px-[30px] pt-[24px] text-[13px] leading-[1.6] text-subtext">{children}</p>
}
