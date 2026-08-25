import docIcon from '../assets/icons/emoji-doc.png'
import targetIcon from '../assets/icons/emoji-target.svg'
import warningIcon from '../assets/icons/emoji-warning.svg'

/**
 * Figma에서 내보낸 이모지 아이콘.
 *
 * 원본은 글리프마다 잉크가 박스 안에서 다른 위치에 있었다 (🎯 중심 y=14.25, ⚠️ 중심 y=15.44).
 * 같은 크기로 나란히 놓으면 1.2px씩 어긋나 보였다. SVG의 viewBox를 각자의 잉크 중심으로
 * 다시 맞춰서 고쳤으므로, 여기서는 별도 보정 없이 같은 크기만 주면 된다.
 *
 * block + object-contain 은 <img> 기본 인라인 배치가 만드는 baseline 여백을 없앤다.
 */
export const emoji = {
  doc: docIcon, // 📃 진행한 테스트 수
  target: targetIcon, // 🎯 성공률
  warning: warningIcon, // ⚠️ 이탈률
} as const

export type EmojiName = keyof typeof emoji

export function Emoji({
  name,
  size = 30,
  className = '',
}: {
  name: EmojiName
  size?: number
  className?: string
}) {
  return (
    <img
      src={emoji[name]}
      alt=""
      aria-hidden
      className={`block shrink-0 object-contain ${className}`}
      style={{ width: size, height: size }}
    />
  )
}
