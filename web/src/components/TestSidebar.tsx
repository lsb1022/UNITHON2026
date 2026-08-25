import { useNavigate } from 'react-router-dom'
import { listTests, type TestStats } from '../api/client'
import { useQuery } from '../api/hooks'
import chevronDownIcon from '../assets/icons/chevron-down.svg'
import avatar from '../assets/img/avatar.png'
import { Icon, type IconName } from './Icon'

/**
 * 테스트 상세의 왼쪽 목록 (Figma 264:8035 / 264:8738).
 *
 * 전역 사이드바(프로젝트·팀·크레딧·설정)를 대신한다 — 이 화면에서는 상단 바가
 * 화면 전체 폭을 쓰고, 왼쪽에는 같은 프로젝트의 테스트 목록이 온다.
 */
export function TestSidebar({ projectId, testId }: { projectId: string; testId: string }) {
  return (
    <aside className="flex w-[248px] shrink-0 flex-col border-r border-line bg-white">
      {/* 페르소나 탭은 뺐다. 사람 목록은 본문의 '페르소나별 결과 비교' 표에서
          결과와 함께 봐야 뜻이 있고, 여기서는 이름만 나열돼 누를 것도 없었다. */}
      <div className="flex shrink-0 items-center gap-[6px] px-[30px] pt-[22px] pb-[14px]">
        <Icon name="paper" size={16} />
        <span className="text-[16px] text-ink">테스트</span>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto">
        <TestList projectId={projectId} testId={testId} />
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
