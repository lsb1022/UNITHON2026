import arrowUp2Raw from '../assets/icons/arrow-up-2.svg?raw'
import cardRaw from '../assets/icons/card.svg?raw'
import folderRaw from '../assets/icons/folder.svg?raw'
import graphRaw from '../assets/icons/graph.svg?raw'
import listRaw from '../assets/icons/list.svg?raw'
import paperRaw from '../assets/icons/paper.svg?raw'
import peopleRaw from '../assets/icons/people.svg?raw'
import personaTabRaw from '../assets/icons/persona-tab.svg?raw'
import settingRaw from '../assets/icons/setting.svg?raw'
import stepsRaw from '../assets/icons/steps.svg?raw'
import teamRaw from '../assets/icons/team.svg?raw'
import userProfileRaw from '../assets/icons/user-profile.svg?raw'

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
  // 테스트 상세 (Figma 264:8033 / 276:3101)
  paper: paperRaw, // 사이드바 '테스트' 탭
  personaTab: personaTabRaw, // 사이드바 '페르소나' 탭
  userProfile: userProfileRaw, // 페르소나 한 명
  list: listRaw, // 보기 전환 '경로'
  graph: graphRaw, // 보기 전환 '다이어그램'
  people: peopleRaw, // 경로 카드의 인원
  steps: stepsRaw, // 경로 카드의 스텝 수
  arrowUp2: arrowUp2Raw, // '히트맵 보기' 꺾쇠
} as const

export type IconName = keyof typeof RAW

/** Figma 내보내기에 박혀 있는 아이콘 색(메인/서브테스트) */
const HARDCODED_COLOR = /(fill|stroke)="(#3182F6|#737373)"/gi

function recolor(svg: string, size: number) {
  return (
    svg
      .replace(HARDCODED_COLOR, '$1="currentColor"')
      // 내보내기에 preserveAspectRatio="none" 이 박혀 있다. 정사각형이 아닌 아이콘
      // (akar-icons:paper 는 12.17×14.83)을 정사각형 칸에 넣으면 그대로 늘어난다.
      // 지우면 기본값(meet)으로 비율을 지키며 가운데에 놓인다.
      .replace(/\spreserveAspectRatio="none"/, '')
      .replace(/\swidth="[\d.]+"/, ` width="${size}"`)
      .replace(/\sheight="[\d.]+"/, ` height="${size}"`)
  )
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
