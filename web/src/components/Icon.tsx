import cardRaw from '../assets/icons/card.svg?raw'
import folderRaw from '../assets/icons/folder.svg?raw'
import settingRaw from '../assets/icons/setting.svg?raw'
import teamRaw from '../assets/icons/team.svg?raw'

/**
 * Figma에서 내보낸 아이콘 원본(SVG)을 그대로 인라인한다.
 * 사이드바 메뉴는 선택 여부에 따라 색이 바뀌므로, 원본에 박혀 있는 색만
 * currentColor로 치환해 벡터 데이터는 손대지 않는다.
 */
const RAW = {
  folder: folderRaw,
  team: teamRaw,
  card: cardRaw,
  setting: settingRaw,
} as const

export type IconName = keyof typeof RAW

/** Figma 내보내기에 박혀 있는 아이콘 색(메인/서브테스트) */
const HARDCODED_COLOR = /(fill|stroke)="(#3182F6|#737373)"/gi

function recolor(svg: string, size: number) {
  return svg
    .replace(HARDCODED_COLOR, '$1="currentColor"')
    .replace(/\swidth="[\d.]+"/, ` width="${size}"`)
    .replace(/\sheight="[\d.]+"/, ` height="${size}"`)
}

export function Icon({
  name,
  size = 24,
  className = '',
}: {
  name: IconName
  size?: number
  className?: string
}) {
  return (
    <span
      aria-hidden
      className={`inline-flex shrink-0 ${className}`}
      style={{ width: size, height: size }}
      dangerouslySetInnerHTML={{ __html: recolor(RAW[name], size) }}
    />
  )
}
