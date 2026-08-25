import type { ReactNode } from 'react'
import { Sidebar } from './Sidebar'

type AppLayoutProps = {
  /** 상단 바 내부에 놓이는 내용(브레드크럼, 스텝 인디케이터 등). 없으면 빈 바로 그려진다. */
  topBar?: ReactNode
  /** 화면 하단에 고정되는 액션 바(마법사 이전/다음). */
  footer?: ReactNode
  children: ReactNode
}

export function AppLayout({ topBar, footer, children }: AppLayoutProps) {
  return (
    <div className="flex h-full min-h-screen bg-bg">
      <Sidebar />

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex h-[70px] shrink-0 items-center border-b border-line bg-white px-[30px]">
          {topBar}
        </header>

        <main className="min-h-0 flex-1 overflow-y-auto">{children}</main>

        {footer ? (
          <footer className="flex h-[103px] shrink-0 items-center justify-between border-t border-divider bg-white px-[50px]">
            {footer}
          </footer>
        ) : null}
      </div>
    </div>
  )
}

/** 본문 공통 여백. 디자인상 콘텐츠는 사이드바에서 72px 떨어진 지점에서 시작한다. */
export function PageBody({
  children,
  className = '',
}: {
  children: ReactNode
  className?: string
}) {
  return <div className={`px-[72px] pt-[56px] pb-[60px] ${className}`}>{children}</div>
}

export function PageHeading({ title, description }: { title: string; description: string }) {
  return (
    <div>
      <h1 className="text-[34px] leading-[1.45] font-bold text-ink">{title}</h1>
      <p className="mt-[8px] text-[15px] text-subtext">{description}</p>
    </div>
  )
}
