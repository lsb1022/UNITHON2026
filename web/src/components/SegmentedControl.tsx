import type { ReactNode } from 'react'

type Option<T extends string> = {
  value: T
  label: string
  icon?: ReactNode
}

type SegmentedControlProps<T extends string> = {
  options: readonly Option<T>[]
  value: T
  onChange: (value: T) => void
  className?: string
}

export function SegmentedControl<T extends string>({
  options,
  value,
  onChange,
  className = '',
}: SegmentedControlProps<T>) {
  return (
    <div
      role="tablist"
      className={`flex h-[48px] items-center gap-[6px] rounded-full border border-line bg-segment-bg p-[6px] ${className}`}
    >
      {options.map((option) => {
        const active = option.value === value
        return (
          <button
            key={option.value}
            role="tab"
            aria-selected={active}
            onClick={() => onChange(option.value)}
            className={`flex h-[34px] flex-1 items-center justify-center gap-[6px] rounded-full px-[10px] font-noto text-[13px] font-medium whitespace-nowrap transition-colors ${
              active
                ? 'border border-line bg-white text-heading'
                : 'border border-transparent text-body hover:text-heading'
            }`}
          >
            {option.icon}
            {option.label}
          </button>
        )
      })}
    </div>
  )
}
