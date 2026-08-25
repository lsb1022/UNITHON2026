import { useEffect, useRef } from 'react'
import type { StepClick, StepDot } from '../api/client'

/**
 * 화면 사진 위에 눌린 자리를 얹는다 (Figma 290:11203).
 *
 * 한 단계에서 벌어지는 클릭은 서너 번뿐이라 그것만으로는 열지도가 되지 않는다.
 * 그래서 두 겹으로 그린다 — 그 **화면 전체**에서 벌어진 클릭을 옅게 깔아 열기를
 * 만들고, **이 단계**의 클릭만 그 위에 또렷한 고리로 얹는다. 배경은 "여기가 늘
 * 붐빈다", 고리는 "지금 이 순간 여기를 눌렀다"를 말한다.
 *
 * Canvas 로 그리는 이유: 40개 넘는 흐릿한 원을 SVG filter 로 겹치면 눈에 띄게 버벅인다.
 */

/** 열기 한 점의 반지름(페이지 좌표 기준). 손가락 하나 크기쯤. */
const BLOB = 52
/** 헛클릭은 눈에 띄어야 한다 — 붉은 고리. */
const WASTED = '#df2d48'
const LANDED = '#00824f'

export function ClickHeatmap({
  shot,
  clicks,
  background,
  width,
  onPick,
  picked,
}: {
  shot: { src: string; w: number; h: number }
  clicks: StepClick[]
  background: StepDot[]
  /** 화면에 실제로 그려질 너비. 사진 원본 너비와 달라도 좌표를 맞춰준다. */
  width: number
  onPick?: (click: StepClick | null) => void
  picked?: StepClick | null
}) {
  const canvas = useRef<HTMLCanvasElement>(null)
  const scale = width / shot.w
  const height = Math.round(shot.h * scale)

  useEffect(() => {
    const el = canvas.current
    if (!el) return
    const dpr = window.devicePixelRatio || 1
    el.width = Math.round(width * dpr)
    el.height = Math.round(height * dpr)
    const ctx = el.getContext('2d')
    if (!ctx) return
    ctx.setTransform(dpr * scale, 0, 0, dpr * scale, 0, 0)
    ctx.clearRect(0, 0, shot.w, shot.h)

    // ① 열기: 같은 자리에 여러 번 눌릴수록 짙어지도록 겹쳐 칠한다.
    ctx.globalCompositeOperation = 'lighter'
    for (const dot of background) {
      const g = ctx.createRadialGradient(dot.x, dot.y, 0, dot.x, dot.y, BLOB)
      const hue = dot.wasted ? '223,45,72' : '0,130,79'
      g.addColorStop(0, `rgba(${hue},0.42)`)
      g.addColorStop(0.55, `rgba(${hue},0.14)`)
      g.addColorStop(1, `rgba(${hue},0)`)
      ctx.fillStyle = g
      ctx.beginPath()
      ctx.arc(dot.x, dot.y, BLOB, 0, Math.PI * 2)
      ctx.fill()
    }

    // ② 이 단계의 클릭: 실제로 눌린 사각형에 고리를 두른다.
    ctx.globalCompositeOperation = 'source-over'
    for (const c of clicks) {
      const on = picked?.persona === c.persona && picked?.x === c.x && picked?.y === c.y
      ctx.strokeStyle = c.wasted ? WASTED : LANDED
      ctx.lineWidth = (on ? 4 : 2.5) / scale
      ctx.setLineDash(c.wasted ? [] : [])
      const w = Math.max(c.w, 18)
      const h = Math.max(c.h, 18)
      ctx.beginPath()
      ctx.roundRect(c.x - w / 2, c.y - h / 2, w, h, 6 / scale)
      ctx.stroke()
      if (on) {
        ctx.fillStyle = c.wasted ? 'rgba(223,45,72,0.18)' : 'rgba(0,130,79,0.18)'
        ctx.fill()
      }
    }
  }, [shot, clicks, background, width, height, scale, picked])

  return (
    <div className="relative" style={{ width, height }}>
      <img
        src={shot.src}
        alt=""
        width={width}
        height={height}
        className="block rounded-[6px]"
        style={{ width, height }}
      />
      <canvas
        ref={canvas}
        style={{ width, height }}
        className="pointer-events-none absolute inset-0"
      />
      {/* 클릭 지점마다 투명한 단추를 얹어 짚을 수 있게 한다. canvas 위에 직접
          hit-test 를 구현하는 것보다 접근성(키보드 이동)이 낫다. */}
      {clicks.map((c, i) => (
        <button
          key={`${c.persona}-${i}`}
          type="button"
          title={`${c.label || '이름 없는 요소'} · ${c.wasted ? '눌러도 아무 일 없음' : '반응함'} · ${c.persona}`}
          onClick={() => onPick?.(picked?.persona === c.persona ? null : c)}
          className="absolute rounded-[6px] focus-visible:outline focus-visible:outline-2 focus-visible:outline-main"
          style={{
            left: (c.x - Math.max(c.w, 18) / 2) * scale,
            top: (c.y - Math.max(c.h, 18) / 2) * scale,
            width: Math.max(c.w, 18) * scale,
            height: Math.max(c.h, 18) * scale,
          }}
        />
      ))}
    </div>
  )
}
