import { Link, NavLink } from 'react-router-dom'
import chevronDownIcon from '../assets/icons/chevron-down.svg'
import sidebarToggleIcon from '../assets/icons/sidebar-toggle.svg'
import avatar from '../assets/img/avatar.png'
import logo from '../assets/img/logo.svg'
import { useSidebar } from '../state/SidebarContext'
import { Icon, type IconName } from './Icon'

const NAV: { to: string; label: string; icon: IconName }[] = [
  { to: '/projects', label: '프로젝트', icon: 'folder' },
  { to: '/compare', label: '사이트 비교', icon: 'graph' },
  { to: '/team', label: '팀 워크스페이스', icon: 'team' },
  { to: '/credit', label: '크레딧 및 플랜', icon: 'card' },
  { to: '/settings', label: '설정', icon: 'setting' },
]

export function Sidebar() {
  const { collapsed, toggle } = useSidebar()

  return (
    <aside
      className={`flex shrink-0 flex-col border-r border-line bg-white transition-[width] duration-200 ${
        collapsed ? 'w-[83px]' : 'w-[248px]'
      }`}
    >
      {collapsed ? (
        // 접힘: 로고 자리 사각형 하나만 (Figma 184:357)
        <div className="flex justify-center pt-[25px]">
          <button
            type="button"
            onClick={toggle}
            aria-label="사이드바 펼치기"
            className="size-[38px] rounded-[10px] bg-[#d9d9d9] transition-opacity hover:opacity-80"
          />
        </div>
      ) : (
        <div className="relative px-[19px] pt-[27px]">
          {/* 서비스명 텍스트가 로고 이미지로 바뀌었다 (Figma 190:2807, 86×27.2).
              로고를 누르면 첫 화면(프로젝트 목록)으로 돌아간다. */}
          <Link to="/projects" aria-label="첫 화면으로" className="inline-block">
            <img src={logo} alt="서비스 로고" className="h-[27.2px] w-[86px]" />
          </Link>
          <button
            type="button"
            onClick={toggle}
            aria-label="사이드바 접기"
            className="absolute top-[27px] right-[17px]"
          >
            <img src={sidebarToggleIcon} alt="" className="size-[24px]" />
          </button>
        </div>
      )}

      <nav className="mt-[25px] flex flex-col">
        {NAV.map(({ to, label, icon }) => (
          <NavLink
            key={to}
            to={to}
            title={collapsed ? label : undefined}
            className={`flex h-[55px] items-center ${collapsed ? 'px-0' : 'px-[15px]'}`}
          >
            {({ isActive }) => (
              <span
                className={`flex h-[49px] flex-1 items-center transition-colors ${
                  collapsed
                    ? 'justify-center rounded-none'
                    : 'gap-[12px] rounded-[16px] px-[15px]'
                } ${
                  isActive
                    ? 'bg-main-soft font-semibold text-main'
                    : 'font-medium text-subtext hover:bg-black/[0.03]'
                }`}
              >
                <Icon name={icon} />
                {collapsed ? null : <span className="text-[15px] leading-[1.45]">{label}</span>}
              </span>
            )}
          </NavLink>
        ))}
      </nav>

      {/* 사이드바 테두리는 오른쪽 한 줄뿐이다 (Figma 184:372 / 184:336).
          프로필 블록 위에는 구분선이 없다 — 넣으면 디자인에 없는 선이 하나 더 생긴다. */}
      <div
        className={`mt-auto flex h-[70px] items-center ${
          collapsed ? 'justify-center px-0' : 'px-[30px]'
        }`}
      >
        <button type="button" className="flex items-center gap-[7px]">
          <img src={avatar} alt="" className="size-[35px] rounded-full object-cover" />
          {collapsed ? null : (
            <>
              <span className="text-[20px] text-ink">영찬</span>
              <span className="text-[13px] leading-[1.45] font-medium text-subtext">Pro</span>
              <img src={chevronDownIcon} alt="" className="size-[24px]" />
            </>
          )}
        </button>
      </div>
    </aside>
  )
}
