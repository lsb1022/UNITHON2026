import { useCallback, useEffect, useState } from 'react'
import { namesOn, personaName, setNamesOn, subscribeNames } from '../lib/personaNames'

/**
 * 페르소나를 무엇으로 부를지 — P001 인가, 최지훈인가.
 *
 * 데이터에는 이름이 없다. 특성 네 축으로만 정의되고 나이·성별은 사용자가 정한
 * 값이다. 이름은 **화면이 붙이는 딱지**이고, 보는 사람이 켜고 끈다:
 * 회의실에서는 "최지훈이 포기했다"가 잘 전달되고, 데이터를 파는 사람에게는
 * P002 가 편하다. 둘 중 하나를 우리가 골라줄 이유가 없다.
 */

/** 지금 설정에 맞는 표시 이름을 돌려주는 함수. 설정이 바뀌면 다시 그려진다. */
export function usePersonaLabel(): (id: string) => string {
  const [on, setOn] = useState(namesOn)
  useEffect(() => subscribeNames(() => setOn(namesOn())), [])
  return useCallback((id: string) => (on ? personaName(id) : id), [on])
}

export function PersonaNameToggle({ className = '' }: { className?: string }) {
  const [on, setOn] = useState(namesOn)
  useEffect(() => subscribeNames(() => setOn(namesOn())), [])

  return (
    <button
      type="button"
      role="switch"
      aria-checked={on}
      onClick={() => setNamesOn(!on)}
      title={on ? '번호(P001)로 보기' : '이름(최지훈)으로 보기'}
      className={`flex items-center gap-[6px] rounded-[8px] border border-line px-[9px] py-[4px] text-[12px] font-medium transition-colors hover:bg-black/[0.03] ${className}`}
    >
      <span className={on ? 'text-main' : 'text-subtext'}>{on ? '이름' : '번호'}</span>
      <span
        className={`relative h-[14px] w-[26px] rounded-full transition-colors ${
          on ? 'bg-main' : 'bg-line'
        }`}
      >
        <span
          className={`absolute top-[2px] size-[10px] rounded-full bg-white transition-[left] ${
            on ? 'left-[14px]' : 'left-[2px]'
          }`}
        />
      </span>
    </button>
  )
}

/**
 * 동그란 얼굴 자리 (Figma 290:11542).
 *
 * 사진은 없다. 지어낸 얼굴을 붙이면 없는 사람을 있는 것처럼 보이게 한다.
 * 대신 id 마다 같은 색이 나오게 해서, 목록에서 같은 사람을 눈으로 좇을 수 있게 한다.
 */
const TONES = [
  ['#e8eefc', '#3f6ad8'],
  ['#eaf7ef', '#00824f'],
  ['#fdeef0', '#df2d48'],
  ['#f4eefc', '#7b4fd8'],
  ['#fdf5e6', '#9a6b1a'],
  ['#e9f6f8', '#0f7d92'],
]

export function PersonaFace({ id, size = 38 }: { id: string; size?: number }) {
  const on = namesOn()
  let h = 0
  for (let i = 0; i < id.length; i++) h = (h * 31 + id.charCodeAt(i)) >>> 0
  const [bg, fg] = TONES[h % TONES.length]
  // 이름을 켰으면 성 한 글자, 껐으면 번호 두 자리. 자리 크기는 같다.
  const mark = on ? personaName(id).slice(0, 1) : id.replace(/^P0*/, '').padStart(2, '0')

  return (
    <span
      aria-hidden
      className="flex shrink-0 items-center justify-center rounded-full text-[13px] font-bold"
      style={{ width: size, height: size, backgroundColor: bg, color: fg }}
    >
      {mark}
    </span>
  )
}
