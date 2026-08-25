import checkMark from '../assets/icons/check-mark.svg'
import stepChevron from '../assets/icons/step-chevron.svg'

export const WIZARD_STEPS = ['새 테스트 설정', '미션 설정', '페르소나', '확인'] as const

export type WizardStep = 1 | 2 | 3 | 4

export function StepIndicator({ current }: { current: WizardStep }) {
  return (
    <ol className="flex items-center gap-[20px]">
      {WIZARD_STEPS.map((label, index) => {
        const step = index + 1
        const done = step < current
        const active = step === current
        return (
          <li key={label} className="contents">
            {index > 0 ? (
              <img src={stepChevron} alt="" aria-hidden className="h-[13px] w-[6.5px]" />
            ) : null}
            <div className={`flex items-center gap-[6px] ${done || active ? '' : 'opacity-60'}`}>
              <span
                className={`grid size-[29px] place-items-center rounded-full text-[12px] ${
                  done
                    ? 'bg-main'
                    : active
                      ? 'border border-line bg-white font-bold text-main'
                      : 'border border-line text-subtext'
                }`}
              >
                {done ? (
                  <img src={checkMark} alt="" aria-hidden className="size-[15px]" />
                ) : (
                  step
                )}
              </span>
              <span
                className={`text-[13px] leading-[1.45] whitespace-nowrap ${
                  active ? 'font-bold text-heading' : 'font-medium text-subtext'
                }`}
              >
                {label}
              </span>
            </div>
          </li>
        )
      })}
    </ol>
  )
}

/** 상단 바: 왼쪽 브레드크럼 + 스텝 인디케이터. 스텝이 없으면 브레드크럼만 보인다. */
export function WizardTopBar({
  breadcrumb,
  current,
}: {
  breadcrumb: { project?: string; page: string }
  current?: WizardStep
}) {
  return (
    <div className="flex w-full items-center gap-[40px]">
      <p className="flex shrink-0 items-center gap-[4px] leading-[1.45] whitespace-nowrap text-heading">
        {breadcrumb.project ? (
          <span className="text-[20px] font-semibold">{breadcrumb.project} /</span>
        ) : null}
        <span className={breadcrumb.project ? 'text-[15px]' : 'text-[16px] font-medium text-body'}>
          {breadcrumb.page}
        </span>
      </p>
      {current ? (
        <div className="flex flex-1 justify-center pr-[251px]">
          <StepIndicator current={current} />
        </div>
      ) : null}
    </div>
  )
}
