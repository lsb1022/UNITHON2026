import type { ReactNode } from 'react'
import { NavLink } from 'react-router-dom'
import { AppLayout } from './AppLayout'

/**
 * 설정 화면의 뼈대 (Figma 311:21271 · 336:28072 · 311:21384).
 *
 * 전역 사이드바 오른쪽에 흰 판이 하나 더 붙는다. 세 화면이 이 판을 공유하므로
 * 여기에만 둔다 — 화면마다 따로 그리면 활성 표시가 서로 어긋난다.
 */

const TABS = [
  { to: '/settings', label: '팀 설정', letter: 'T', end: true },
  { to: '/settings/plan', label: '플랜', letter: 'P', end: false },
  { to: '/settings/credit', label: '크레딧', letter: 'C', end: false },
]

export function SettingsLayout({
  title,
  description,
  children,
}: {
  title: string
  description: string
  children: ReactNode
}) {
  return (
    <AppLayout>
      <div className="flex min-h-full">
        <nav className="w-[286px] shrink-0 border-r border-divider bg-white pt-[42px]">
          {TABS.map((tab) => (
            <NavLink key={tab.to} to={tab.to} end={tab.end} className="block">
              {({ isActive }) => (
                <span
                  className={`relative flex h-[55px] items-center gap-[13px] px-[34px] transition-colors ${
                    isActive ? 'bg-brand-soft' : 'hover:bg-black/[0.02]'
                  }`}
                >
                  {/* 왼쪽 세로 막대가 '지금 어디' 를 말한다. 배경색만으로는
                      옅어서 판 전체가 하나로 보인다. */}
                  {isActive ? (
                    <span className="absolute top-[4px] bottom-[4px] left-0 w-[3px] rounded-r-full bg-main" />
                  ) : null}
                  <span
                    className={`grid size-[40px] place-items-center rounded-[12px] text-[14px] font-semibold ${
                      isActive ? 'bg-main text-white' : 'bg-track text-muted'
                    }`}
                  >
                    {tab.letter}
                  </span>
                  <span
                    className={`text-[14px] font-medium ${isActive ? 'text-main' : 'text-body'}`}
                  >
                    {tab.label}
                  </span>
                </span>
              )}
            </NavLink>
          ))}
        </nav>

        <div className="min-w-0 flex-1 px-[104px] pt-[64px] pb-[60px]">
          <h1 className="text-[26px] leading-[1.4] font-bold text-heading">{title}</h1>
          <p className="mt-[10px] text-[14px] text-muted">{description}</p>
          <div className="mt-[52px]">{children}</div>
        </div>
      </div>
    </AppLayout>
  )
}

/** 설정 화면의 흰 카드. 셋 다 같은 테두리·모서리를 쓴다. */
export function SettingsCard({
  children,
  className = '',
}: {
  children: ReactNode
  className?: string
}) {
  return (
    <section className={`rounded-[16px] border border-divider bg-white ${className}`}>
      {children}
    </section>
  )
}
