import { Link, NavLink } from 'react-router-dom'
import sidebarToggleIcon from '../assets/icons/sidebar-toggle.svg'
import logo from '../assets/img/logo.svg'
import { useSidebar } from '../state/SidebarContext'
import { Icon, type IconName } from './Icon'
import { ProfileMenu } from './ProfileMenu'

/**
 * 전역 메뉴 (Figma 336:28021).
 *
 * 네 개뿐이다. '사이트 비교'는 A/B 테스트가 흡수했고, '팀 워크스페이스'는
 * 설정 안의 '팀 설정'으로 들어갔다 — 누를 데가 두 곳이면 어느 쪽이 정본인지
 * 알 수 없어진다.
 */
const NAV: { to: string; label: string; icon: IconName }[] = [
  { to: '/projects', label: '프로젝트', icon: 'folder' },
  { to: '/ab', label: 'A/B 테스트', icon: 'abTest' },
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
        // 접힘: 파란 사각형 안에 로고 (Figma 184:357)
        // 회색 자리표시자로 두면 로고를 아직 안 넣은 화면처럼 보인다.
        // 펼침 상태와 같은 svg 를 쓰고 색만 뒤집는다 — 파일이 둘이면 어긋난다.
        <div className="flex justify-center pt-[25px]">
          <button
            type="button"
            onClick={toggle}
            aria-label="사이드바 펼치기"
            className="grid size-[38px] place-items-center rounded-[10px] bg-main transition-opacity hover:opacity-85"
          >
            <img
              src={logo}
              alt="서비스 로고"
              className="w-[26px] brightness-0 invert"
            />
          </button>
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
      <div className="mt-auto">
        <ProfileMenu collapsed={collapsed} />
      </div>
    </aside>
  )
}
