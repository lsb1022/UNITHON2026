/** 조회 중 / 실패 표시. 화면마다 다르게 만들면 실패가 조용히 빈 화면으로 보인다. */
export function LoadingBlock({ label = '불러오는 중이에요' }: { label?: string }) {
  return (
    <div className="flex h-[240px] items-center justify-center gap-[12px] text-[15px] text-subtext">
      <span className="size-[20px] animate-spin rounded-full border-2 border-main border-t-transparent" />
      {label}
    </div>
  )
}

export function ErrorBlock({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div className="flex h-[240px] flex-col items-center justify-center gap-[12px] rounded-[16px] border border-danger/40 bg-danger-bg/60 px-[24px] text-center">
      <p className="text-[16px] font-bold text-danger">불러오지 못했어요</p>
      <p className="text-[14px] text-body">{message}</p>
      {onRetry ? (
        <button
          type="button"
          onClick={onRetry}
          className="mt-[4px] rounded-[12px] border border-line bg-white px-[18px] py-[9px] text-[14px] font-semibold text-heading hover:bg-black/[0.03]"
        >
          다시 시도
        </button>
      ) : null}
    </div>
  )
}
