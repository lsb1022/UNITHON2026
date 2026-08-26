/**
 * 테스트 진행중 배너 (Figma 130:11451).
 * 프로젝트 목록과 프로젝트 상세 상단에 같은 모양으로 얹힌다.
 *
 * 배너 전체가 진행 화면으로 가는 통로다. 진행중인 것을 보여주면서 거기로 가는
 * 길을 안 주면, 사용자는 목록에서 프로젝트를 다시 찾아 들어가야 한다.
 */
export type RunProgress = {
  projectName: string
  testName: string
  done: number
  total: number
  /** 남은 시간(분). 모르면 생략한다 — 가짜 숫자를 보여주지 않는다. */
  minutesLeft?: number
  /** 서버가 계산한 진행률. 답사 단계에서도 오른다. */
  percent?: number
}

export function RunProgressBanner({
  progress,
  onOpen,
}: {
  progress: RunProgress
  /** 진행 화면으로 데려간다. 없으면 배너는 그냥 표시만 한다. */
  onOpen?: () => void
}) {
  const { projectName, testName, done, total, minutesLeft } = progress
  const percent = progress.percent ?? (total > 0 ? Math.round((done / total) * 100) : 0)

  const Shell = onOpen ? 'button' : 'section'

  return (
    <Shell
      {...(onOpen
        ? { type: 'button' as const, onClick: onOpen, 'aria-label': '진행중인 테스트 보기' }
        : { 'aria-label': '진행중인 테스트' })}
      className={`relative block w-full rounded-[22px] border border-line bg-white px-[23px] pt-[46px] pb-[24px] text-left ${
        onOpen ? 'cursor-pointer transition-colors hover:border-main/60 hover:bg-main/[0.02]' : ''
      }`}
    >
      <div className="flex flex-col gap-[5px]">
        {/* 이름이 길면 진행률 숫자를 뚫고 나갔다. 오른쪽 자리를 비워 두고 접는다. */}
        <div className="flex items-baseline gap-[8px] pr-[150px] text-ink">
          <p className="min-w-0 truncate text-[28px] leading-[1.45] font-bold">
            {projectName} / {testName}
          </p>
          <p className="shrink-0 text-[20px] leading-[1.45] font-medium">진행중</p>
        </div>
        <p className="font-noto text-[15px] leading-[1.45] font-medium text-subtext">
          {done} / {total}명이 테스트를 마쳤어요
        </p>
      </div>

      <div
        role="progressbar"
        aria-valuenow={percent}
        aria-valuemin={0}
        aria-valuemax={100}
        className="mt-[22px] h-[14px] w-full overflow-hidden rounded-[7px] bg-track"
      >
        <div
          className="h-full rounded-[7px] bg-main transition-[width] duration-500"
          style={{ width: `${percent}%` }}
        />
      </div>

      <div className="absolute top-[38px] right-[23px] flex flex-col items-end">
        <p className="text-[40px] leading-[1.45] font-bold text-ink">{percent}%</p>
        {minutesLeft !== undefined ? (
          <p className="mt-[6px] text-[16px] leading-[1.45] text-subtext">
            예상 {minutesLeft}분 남음
          </p>
        ) : null}
      </div>
    </Shell>
  )
}
