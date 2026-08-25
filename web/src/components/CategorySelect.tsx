import { useEffect, useRef, useState } from 'react'
import chevronDownIcon from '../assets/icons/chevron-down.svg'

/**
 * 프로젝트 카테고리.
 *
 * 자유 입력이면 "쇼핑몰"과 "커머스"가 서로 다른 그룹이 되어 카테고리별 탭이 무의미해진다.
 * 목록을 고정해 두고, 서버도 같은 목록으로 검증한다 (app/categories.py).
 */
export const CATEGORIES = [
  '커머스',
  '푸드',
  '미디어',
  '트래블',
  '헬스',
  '금융',
  '교육',
  '생산성',
  '기타',
] as const

export type Category = (typeof CATEGORIES)[number]

export function CategorySelect({
  value,
  onChange,
}: {
  value: string
  onChange: (value: Category) => void
}) {
  const [open, setOpen] = useState(false)
  const rootRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!open) return

    const onPointerDown = (event: MouseEvent) => {
      if (!rootRef.current?.contains(event.target as Node)) setOpen(false)
    }
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setOpen(false)
    }

    document.addEventListener('mousedown', onPointerDown)
    document.addEventListener('keydown', onKeyDown)
    return () => {
      document.removeEventListener('mousedown', onPointerDown)
      document.removeEventListener('keydown', onKeyDown)
    }
  }, [open])

  return (
    <div ref={rootRef} className="relative w-full max-w-[1100px]">
      <button
        type="button"
        aria-haspopup="listbox"
        aria-expanded={open}
        onClick={() => setOpen((prev) => !prev)}
        className={`flex h-[62px] w-full items-center rounded-[16px] border bg-white px-[21px] text-left transition-colors ${
          open ? 'border-main' : 'border-line hover:border-[#c2c2c2]'
        }`}
      >
        <span className={`text-[15px] leading-[1.45] ${value ? 'text-ink' : 'text-placeholder'}`}>
          {value || '카테고리를 골라주세요'}
        </span>
        <img
          src={chevronDownIcon}
          alt=""
          aria-hidden
          className={`ml-auto size-[24px] transition-transform ${open ? 'rotate-180' : ''}`}
        />
      </button>

      {open ? (
        <div
          role="listbox"
          className="absolute top-[70px] left-0 z-30 max-h-[360px] w-full overflow-y-auto rounded-[16px] border border-line bg-white py-[8px] shadow-[0_12px_32px_rgba(0,0,0,0.12)]"
        >
          {CATEGORIES.map((category) => {
            const active = category === value
            return (
              <button
                key={category}
                role="option"
                aria-selected={active}
                onClick={() => {
                  onChange(category)
                  setOpen(false)
                }}
                className={`flex w-full items-center px-[21px] py-[11px] text-left text-[15px] transition-colors ${
                  active ? 'bg-main-soft font-semibold text-main' : 'text-ink hover:bg-black/[0.03]'
                }`}
              >
                {category}
              </button>
            )
          })}
        </div>
      ) : null}
    </div>
  )
}
