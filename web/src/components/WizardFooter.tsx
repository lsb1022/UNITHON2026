import arrowIcon from '../assets/icons/arrow.svg'

type WizardFooterProps = {
  onPrev: () => void
  onNext: () => void
  nextLabel?: string
  prevLabel?: string
  nextDisabled?: boolean
}

export function WizardFooter({
  onPrev,
  onNext,
  nextLabel = '다음',
  prevLabel = '이전',
  nextDisabled = false,
}: WizardFooterProps) {
  return (
    <>
      <button
        type="button"
        onClick={onPrev}
        className="h-[65px] w-[179px] rounded-[14px] border border-line bg-white text-[20px] leading-[1.45] font-medium text-heading transition-colors hover:bg-black/[0.03]"
      >
        {prevLabel}
      </button>
      <button
        type="button"
        onClick={onNext}
        disabled={nextDisabled}
        className="flex h-[65px] w-[179px] items-center justify-center gap-[5px] rounded-[14px] bg-main text-[20px] leading-[1.45] font-medium text-white transition-colors hover:bg-[#2872dd] disabled:cursor-not-allowed disabled:bg-[#c4d9f9]"
      >
        {nextLabel}
        <img src={arrowIcon} alt="" aria-hidden className="size-[15px]" />
      </button>
    </>
  )
}
