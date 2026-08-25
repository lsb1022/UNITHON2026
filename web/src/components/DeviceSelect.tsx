import { useEffect, useRef, useState } from 'react'
import chevronDownIcon from '../assets/icons/chevron-down.svg'
import deviceIcon from '../assets/icons/device.svg'

export type DevicePreset = {
  id: string
  label: string
  width: number
  height: number
  group: string
  /** 화면에 함께 보여줄 한 줄 설명 */
  note?: string
}

/**
 * 실행 환경 프리셋.
 * 1280×800 과 375×667 에는 설명을 붙였다 — 기획서가 "375px에서만 드러나는 3건은
 * 원리적으로 못 잡는다"고 상한을 못박았기 때문에, 뷰포트 선택이 결과의 의미를 바꾼다.
 */
export const DEVICE_PRESETS: DevicePreset[] = [
  { id: 'desktop-16-9', label: '데스크탑 16:9', width: 1920, height: 1080, group: '데스크탑' },
  { id: 'desktop-16-10', label: '데스크탑 16:10', width: 1680, height: 1050, group: '데스크탑' },
  { id: 'laptop-1440', label: '노트북', width: 1440, height: 900, group: '노트북' },
  {
    id: 'laptop-1280',
    label: '노트북 (소형)',
    width: 1280,
    height: 800,
    group: '노트북',
    note: '기본 답사 환경',
  },
  { id: 'tablet-land', label: '태블릿 가로', width: 1024, height: 768, group: '태블릿' },
  { id: 'tablet-port', label: '태블릿 세로', width: 768, height: 1024, group: '태블릿' },
  { id: 'mobile-large', label: '모바일 (대)', width: 428, height: 926, group: '모바일' },
  { id: 'mobile-std', label: '모바일 (표준)', width: 390, height: 844, group: '모바일' },
  {
    id: 'mobile-small',
    label: '모바일 (소형)',
    width: 375,
    height: 667,
    group: '모바일',
    note: '반응형 결함이 드러나는 폭',
  },
]

const GROUPS = ['데스크탑', '노트북', '태블릿', '모바일']

export function DeviceSelect({
  value,
  onChange,
}: {
  value: string
  onChange: (id: string) => void
}) {
  const [open, setOpen] = useState(false)
  const rootRef = useRef<HTMLDivElement>(null)
  const selected = DEVICE_PRESETS.find((preset) => preset.id === value) ?? DEVICE_PRESETS[0]

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
        className={`flex h-[62px] w-full items-center gap-[9px] rounded-[16px] border bg-white px-[17px] text-left transition-colors ${
          open ? 'border-main' : 'border-line hover:border-[#c2c2c2]'
        }`}
      >
        <img src={deviceIcon} alt="" aria-hidden className="size-[24px]" />
        <span className="text-[15px] leading-[1.45] text-ink">{selected.label}</span>
        <span className="text-[14px] text-subtext">
          {selected.width} × {selected.height}
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
          className="absolute top-[70px] left-0 z-30 max-h-[420px] w-full overflow-y-auto rounded-[16px] border border-line bg-white py-[8px] shadow-[0_12px_32px_rgba(0,0,0,0.12)]"
        >
          {GROUPS.map((group) => (
            <div key={group}>
              <p className="px-[17px] pt-[12px] pb-[6px] text-[12px] font-semibold text-subtext">
                {group}
              </p>
              {DEVICE_PRESETS.filter((preset) => preset.group === group).map((preset) => {
                const active = preset.id === selected.id
                return (
                  <button
                    key={preset.id}
                    role="option"
                    aria-selected={active}
                    onClick={() => {
                      onChange(preset.id)
                      setOpen(false)
                    }}
                    className={`flex w-full items-center gap-[10px] px-[17px] py-[10px] text-left transition-colors ${
                      active ? 'bg-main-soft' : 'hover:bg-black/[0.03]'
                    }`}
                  >
                    <span
                      className={`text-[15px] ${active ? 'font-semibold text-main' : 'text-ink'}`}
                    >
                      {preset.label}
                    </span>
                    <span className="text-[13px] text-subtext">
                      {preset.width} × {preset.height}
                    </span>
                    {preset.note ? (
                      <span className="ml-auto rounded-full bg-track px-[10px] py-[3px] text-[12px] text-body">
                        {preset.note}
                      </span>
                    ) : null}
                  </button>
                )
              })}
            </div>
          ))}
        </div>
      ) : null}
    </div>
  )
}
