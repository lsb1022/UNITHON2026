import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from 'react'

const STORAGE_KEY = 'uxlab:sidebar-collapsed'

type SidebarState = {
  collapsed: boolean
  toggle: () => void
}

const SidebarContext = createContext<SidebarState | null>(null)

/**
 * 사이드바 접힘 상태.
 *
 * 페이지마다 AppLayout 을 따로 그리기 때문에 컴포넌트 안에 두면 이동할 때마다 펴진다.
 * 라우터 바깥에 두고 localStorage 에 적어, 새로고침해도 접은 상태가 남게 한다.
 */
export function SidebarProvider({ children }: { children: ReactNode }) {
  const [collapsed, setCollapsed] = useState(() => {
    if (typeof window === 'undefined') return false
    return window.localStorage.getItem(STORAGE_KEY) === '1'
  })

  useEffect(() => {
    window.localStorage.setItem(STORAGE_KEY, collapsed ? '1' : '0')
  }, [collapsed])

  const toggle = useCallback(() => setCollapsed((prev) => !prev), [])

  return <SidebarContext.Provider value={{ collapsed, toggle }}>{children}</SidebarContext.Provider>
}

export function useSidebar() {
  const context = useContext(SidebarContext)
  if (!context) throw new Error('useSidebar must be used inside <SidebarProvider>')
  return context
}
