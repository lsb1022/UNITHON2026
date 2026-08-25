/**
 * 테스트 진행중 배너 (Figma 130:11451).
 * 프로젝트 목록과 프로젝트 상세 상단에 같은 모양으로 얹힌다.
 */
export type RunProgress = {
  projectName: string
  testName: string
  done: number
  total: number
  /** 남은 시간(분). 모르면 생략한다 — 가짜 숫자를 보여주지 않는다. */
  minutesLeft?: number
}

export function RunProgressBanner({ progress }: { progress: RunProgress }) {
  const { projectName, testName, done, total, minutesLeft } = progress
  const percent = total > 0 ? Math.round((done / total) * 100) : 0

  return (
    <section
      aria-label="진행중인 테스트"
      className="relative rounded-[22px] border border-line bg-white px-[23px] pt-[46px] pb-[24px]"
    >
      <div className="flex flex-col gap-[5px]">
        <div className="flex items-center gap-[8px] whitespace-nowrap text-ink">
          <p className="text-[32px] leading-[1.45] font-bold">
            {projectName} / {testName}
          </p>
          <p className="text-[24px] leading-[1.45] font-medium">진행중</p>
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
    </section>
  )
}
