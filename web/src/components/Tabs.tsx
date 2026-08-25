type TabsProps<T extends string> = {
  tabs: readonly { value: T; label: string }[]
  value: T
  onChange: (value: T) => void
  className?: string
}

export function Tabs<T extends string>({ tabs, value, onChange, className = '' }: TabsProps<T>) {
  return (
    <div className={`flex border-b border-line ${className}`} role="tablist">
      {tabs.map((tab) => {
        const active = tab.value === value
        return (
          <button
            key={tab.value}
            role="tab"
            aria-selected={active}
            onClick={() => onChange(tab.value)}
            className={`-mb-px w-[115px] border-b-2 pb-[10px] text-[16px] font-medium transition-colors ${
              active ? 'border-main text-main' : 'border-transparent text-subtext hover:text-ink'
            }`}
          >
            {tab.label}
          </button>
        )
      })}
    </div>
  )
}
