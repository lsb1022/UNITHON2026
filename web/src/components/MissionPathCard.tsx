import type { MissionPath } from '../api/client'
import { Icon } from './Icon'
import { SitePreview } from './SitePreview'

/**
 * 경로 카드 한 장 (Figma 264:8143).
 *
 * 화면 칸은 71×72 다. 페르소나가 실제로 지나간 화면을 순서대로 늘어놓고,
 * 카드에 다 못 실은 나머지는 "+3" 으로 접는다.
 */
export function MissionPathCard({
  path,
  onHeatmap,
}: {
  path: MissionPath
  onHeatmap: () => void
}) {
  return (
    <article className="flex flex-col gap-[10px] rounded-[16px] border border-line bg-white p-[18px]">
      <div className="flex h-[46px] items-center justify-between">
        <div className="flex min-w-0 flex-col gap-[2px]">
          <div className="flex h-[24px] items-center gap-[8px]">
            <p className="text-[17px] font-bold text-ink">{path.name}</p>
            <p className="truncate text-[13px] leading-[1.45] font-medium text-subtext">
              {path.label}
            </p>
          </div>
          <div className="flex h-[20px] items-center gap-[12px]">
            <Metric icon="people" text={`${path.persona_count}명`} />
            <Metric icon="steps" text={`${path.step_count} step`} />
          </div>
        </div>

        <button
          type="button"
          onClick={onHeatmap}
          className="flex h-[36px] w-[128px] shrink-0 items-center justify-center rounded-[11px] border border-divider bg-white transition-colors hover:bg-black/[0.03]"
        >
          <span className="text-[13px] leading-[1.45] font-bold text-main">히트맵 보기</span>
          <Icon name="arrowUp2" className="rotate-90 text-main" />
        </button>
      </div>

      <div className="flex items-center gap-[35px]">
        <div className="flex items-center gap-[10px]">
          {path.screens.map((screen, index) => (
            <div
              key={`${screen.key}-${index}`}
              title={screen.title}
              className="h-[72px] w-[71px] shrink-0 overflow-hidden rounded-[4px] border border-line"
            >
              <SitePreview url={screen.url} alt={screen.title} fit="cover" />
            </div>
          ))}
        </div>
        {path.more > 0 ? (
          <p className="text-[15px] leading-[1.45] font-semibold text-subtext">+{path.more}</p>
        ) : null}
      </div>
    </article>
  )
}

function Metric({ icon, text }: { icon: 'people' | 'steps'; text: string }) {
  return (
    <span className="flex items-center justify-center gap-[4px]">
      <Icon name={icon} size={18} className="text-subtext" />
      <span className="text-[12px] leading-[1.45] text-subtext">{text}</span>
    </span>
  )
}
