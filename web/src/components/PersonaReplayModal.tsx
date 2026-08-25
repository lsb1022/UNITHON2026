import { useEffect, useMemo, useRef, useState } from 'react'
import type { PersonaReplay, ReplayFrame } from '../api/client'

/**
 * 한 사람의 여정을 처음부터 끝까지 재생한다.
 *
 * 단계 상세 창은 "이 순간 여기 있던 사람들"을 **가로**로 본다. 여기는 반대로
 * 한 사람을 **세로**로 따라간다 — 어디서 헤맸고 언제 포기했는지는 그 사람의
 * 스텝을 이어서 봐야 보인다.
 *
 * 화면은 답사자가 찍어둔 전체 페이지 사진 한 장을 쓰고, 그 스텝의 스크롤 위치로
 * 밀어 보여준다. 페르소나마다 화면을 다시 찍지 않는 것이 이 파이프라인의
 * 설계라(뒷사람은 글로만 움직인다) 사진은 화면 종류당 한 장뿐이다.
 * 좌표가 문서 절대좌표라 그 위에 누른 자리를 그대로 얹을 수 있다.
 */

/** 사진을 줄여 보여줄 폭. 뷰포트(1280)를 이 폭에 맞춘다.
 *  창이 1240px 이고 왼쪽 목록이 190px 이라 900 이 남는 자리를 거의 채운다 —
 *  작게 두면 글자가 안 읽혀서 '무엇을 보고 있었나'가 전달되지 않는다. */
const STAGE_W = 880
const SPEEDS = [
  { label: '1×', ms: 1600 },
  { label: '2×', ms: 800 },
  { label: '4×', ms: 400 },
]

export function PersonaReplayModal({
  person,
  onClose,
  onPick,
  others,
}: {
  person: PersonaReplay
  onClose: () => void
  /** 다른 사람으로 갈아타기. 목록을 주면 왼쪽에 띄운다. */
  onPick?: (id: string) => void
  others?: PersonaReplay[]
}) {
  const [at, setAt] = useState(0)
  const [playing, setPlaying] = useState(false)
  const [speed, setSpeed] = useState(1)
  const stage = useRef<HTMLDivElement>(null)

  const frames = person.frames
  const frame: ReplayFrame | undefined = frames[at]
  const scale = frame?.shot ? STAGE_W / frame.shot.w : 1
  const stageH = frame ? Math.round((frame.viewport.h || 800) * scale) : 400

  // 사람이 바뀌면 처음부터. 남겨두면 3스텝짜리 사람에게 12스텝 자리가 남는다.
  useEffect(() => {
    setAt(0)
    setPlaying(false)
  }, [person.id])

  useEffect(() => {
    if (!playing) return
    if (at >= frames.length - 1) {
      setPlaying(false)
      return
    }
    const t = window.setTimeout(() => setAt((v) => v + 1), SPEEDS[speed].ms)
    return () => window.clearTimeout(t)
  }, [playing, at, frames.length, speed])

  useEffect(() => {
    const key = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
      if (e.key === 'ArrowLeft') setAt((v) => Math.max(0, v - 1))
      if (e.key === 'ArrowRight') setAt((v) => Math.min(frames.length - 1, v + 1))
      if (e.key === ' ') {
        e.preventDefault()
        setPlaying((v) => !v)
      }
    }
    window.addEventListener('keydown', key)
    return () => window.removeEventListener('keydown', key)
  }, [onClose, frames.length])

  // 화면이 바뀌는 지점. 진행 막대에 눈금으로 찍어 "여기서 넘어갔다"를 보여준다.
  const marks = useMemo(
    () =>
      frames
        .map((f, i) => (i > 0 && f.screen !== frames[i - 1].screen ? i : -1))
        .filter((i) => i >= 0),
    [frames],
  )

  const done = person.outcome === 'success'

  return (
    <div
      className="fixed inset-0 z-[60] flex items-center justify-center bg-black/50 p-[24px]"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose()
      }}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-label={`${person.id} 여정 재생`}
        className="flex max-h-full w-full max-w-[1240px] flex-col overflow-hidden rounded-[18px] bg-white shadow-[0_24px_70px_rgba(0,0,0,0.3)]"
      >
        <header className="flex items-start justify-between gap-[16px] border-b border-line px-[26px] py-[18px]">
          <div>
            <h2 className="flex items-center gap-[10px] text-[19px] leading-[1.4] font-bold text-heading">
              {person.id} 여정 재생
              <span
                className={`rounded-[6px] px-[8px] py-[3px] text-[12px] font-bold text-white ${
                  done ? 'bg-[#00824f]' : 'bg-[#df2d48]'
                }`}
              >
                {done ? '🏆' : '⚑'} {person.end_label}
              </span>
              {person.synthetic ? (
                <span className="rounded-[6px] bg-[#fdf4e3] px-[8px] py-[3px] text-[12px] font-semibold text-[#9a6b1a]">
                  추정 데이터
                </span>
              ) : null}
            </h2>
            <p className="mt-[5px] text-[13px] text-subtext">
              {person.label} · 전체 {person.steps}스텝
            </p>
          </div>
          <button
            type="button"
            aria-label="닫기"
            onClick={onClose}
            className="flex size-[30px] shrink-0 items-center justify-center rounded-[8px] border border-line text-[16px] leading-none text-heading hover:bg-black/[0.04]"
          >
            &times;
          </button>
        </header>

        <div className="flex min-h-0 flex-1">
          {others && others.length > 1 ? (
            <aside className="w-[190px] shrink-0 overflow-y-auto border-r border-line">
              {others.map((o) => (
                <button
                  key={o.id}
                  type="button"
                  onClick={() => onPick?.(o.id)}
                  className={`flex w-full items-center gap-[8px] border-b border-line px-[14px] py-[10px] text-left transition-colors ${
                    o.id === person.id ? 'bg-main/[0.07]' : 'hover:bg-black/[0.02]'
                  }`}
                >
                  <span
                    className={`size-[8px] shrink-0 rounded-full ${
                      o.outcome === 'success' ? 'bg-[#00824f]' : 'bg-[#df2d48]'
                    }`}
                  />
                  <span className="min-w-0 flex-1">
                    <span className="block text-[13px] font-semibold text-heading">{o.id}</span>
                    <span className="block truncate text-[11px] text-subtext">{o.label}</span>
                  </span>
                  <span className="shrink-0 text-[11px] text-subtext tabular-nums">
                    {o.steps}
                  </span>
                </button>
              ))}
            </aside>
          ) : null}

          <div className="flex min-w-0 flex-1 flex-col">
            <div className="flex flex-1 items-center justify-center overflow-auto bg-[#f6f7f9] p-[18px]">
              {frame?.shot ? (
                <div
                  ref={stage}
                  className="relative overflow-hidden rounded-[8px] border border-line bg-white"
                  style={{ width: STAGE_W, height: stageH }}
                >
                  {/* 사진을 그 스텝의 스크롤 위치로 민다. 사람이 그때 본 화면이다. */}
                  <img
                    src={frame.shot.src}
                    alt=""
                    className="absolute left-0 max-w-none transition-[top] duration-500"
                    style={{
                      width: STAGE_W,
                      top: -Math.round(frame.scroll_y * scale),
                    }}
                  />
                  {frame.box ? (
                    <span
                      className="pointer-events-none absolute rounded-[5px] border-2 transition-all duration-300"
                      style={{
                        left: Math.round(frame.box.x * scale),
                        top: Math.round((frame.box.y - frame.scroll_y) * scale),
                        width: Math.round(Math.max(frame.box.w, 16) * scale),
                        height: Math.round(Math.max(frame.box.h, 16) * scale),
                        borderColor: frame.changed ? '#00824f' : '#df2d48',
                        boxShadow: `0 0 0 9999px rgba(0,0,0,0.18)`,
                      }}
                    />
                  ) : null}
                </div>
              ) : (
                <p className="py-[70px] text-center text-[14px] text-subtext">
                  이 화면은 답사자가 찍어둔 사진이 없어요.
                </p>
              )}
            </div>

            {/* 속마음 — 이 창의 알맹이다. 화면보다 이게 먼저 읽혀야 한다. */}
            <div className="border-t border-line px-[22px] py-[14px]">
              <p className="flex items-center gap-[8px] text-[12px] text-subtext">
                <span className="font-semibold text-heading tabular-nums">
                  {frame?.step ?? 0} / {frames.length}
                </span>
                <span className="rounded-[5px] border border-line px-[6px] py-[1px]">
                  {frame?.title}
                </span>
                {frame?.action ? <span>{ACTION[frame.action] ?? frame.action}</span> : null}
                {frame?.target ? <span className="text-body">{frame.target}</span> : null}
                {frame && !frame.changed && frame.action !== 'scroll' ? (
                  <span className="text-[#df2d48]">아무 일도 일어나지 않음</span>
                ) : null}
                {frame?.blocked ? <span className="text-[#9a6b1a]">규칙에 막힘</span> : null}
              </p>
              <blockquote className="mt-[7px] rounded-[10px] border border-main/30 bg-white px-[14px] py-[11px] text-[14px] leading-[1.6] text-body">
                “{frame?.thought}”
              </blockquote>
            </div>

            <div className="flex items-center gap-[12px] border-t border-line px-[22px] py-[12px]">
              <button
                type="button"
                onClick={() => {
                  if (at >= frames.length - 1) setAt(0)
                  setPlaying((v) => !v)
                }}
                className="h-[32px] shrink-0 rounded-[8px] bg-main px-[14px] text-[13px] font-semibold text-white"
              >
                {playing ? '❚❚ 멈춤' : at >= frames.length - 1 ? '↻ 다시' : '▶ 재생'}
              </button>
              <div className="flex shrink-0 rounded-[8px] border border-line p-[2px]">
                {SPEEDS.map((s, i) => (
                  <button
                    key={s.label}
                    type="button"
                    onClick={() => setSpeed(i)}
                    className={`rounded-[6px] px-[8px] py-[3px] text-[12px] font-semibold ${
                      i === speed ? 'bg-main text-white' : 'text-subtext'
                    }`}
                  >
                    {s.label}
                  </button>
                ))}
              </div>

              <div className="relative min-w-0 flex-1">
                <input
                  type="range"
                  min={0}
                  max={Math.max(0, frames.length - 1)}
                  value={at}
                  aria-label="스텝 이동"
                  onChange={(e) => {
                    setPlaying(false)
                    setAt(Number(e.target.value))
                  }}
                  className="w-full cursor-pointer accent-[var(--color-main)]"
                />
                {/* 화면이 바뀐 지점. 눈금이 있어야 "여기서 넘어갔다"가 보인다. */}
                {marks.map((m) => (
                  <span
                    key={m}
                    className="pointer-events-none absolute top-[2px] h-[6px] w-[2px] rounded-[1px] bg-heading/45"
                    style={{ left: `${(m / Math.max(1, frames.length - 1)) * 100}%` }}
                  />
                ))}
              </div>

              <span className="shrink-0 text-[12px] text-subtext tabular-nums">
                {frame?.elapsed_ms ? `${(frame.elapsed_ms / 1000).toFixed(1)}초` : ''}
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

/** 기록의 조작 이름을 사람 말로. */
const ACTION: Record<string, string> = {
  click: '누름',
  type: '입력',
  select: '선택',
  scroll: '스크롤',
  goto: '주소로 이동',
  give_up: '포기',
  done: '완료 선언',
  wait: '기다림',
  back: '뒤로',
}
