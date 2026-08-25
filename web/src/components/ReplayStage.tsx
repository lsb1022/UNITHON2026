import { useEffect, useMemo, useState } from 'react'
import type { PersonaReplay, ReplayFrame } from '../api/client'
import { PersonaFace, usePersonaLabel } from './PersonaIdentity'

/**
 * 한 사람의 여정을 재생하는 **무대**. 창(모달) 껍데기는 없다.
 *
 * 단계 상세 창 안에서도 쓰고, 페르소나 표에서 여는 창에서도 쓴다. 창을 하나 더
 * 띄우면 보던 오른쪽 패널이 가려져서, "이 사람이 지금 뭘 하고 있었나"와
 * "그 자리에 누가 또 있었나"를 동시에 못 본다.
 *
 * 화면은 답사자가 찍어둔 전체 페이지 사진 한 장을 그 스텝의 스크롤 위치로 밀어
 * 보여준다. 페르소나마다 다시 찍지 않는 것이 이 파이프라인의 설계이고, 좌표가
 * 문서 절대좌표라 그 위에 누른 자리를 그대로 얹을 수 있다.
 */

const SPEEDS = [
  { label: '1×', ms: 1600 },
  { label: '2×', ms: 800 },
  { label: '4×', ms: 400 },
]

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

export function ReplayStage({
  person,
  width,
  onExit,
}: {
  person: PersonaReplay
  /** 사진을 그릴 폭. 뷰포트(1280)를 이 폭에 맞춰 줄인다. */
  width: number
  /** 재생을 그만두고 원래 보던 것으로 돌아간다. */
  onExit?: () => void
}) {
  const [at, setAt] = useState(0)
  const [playing, setPlaying] = useState(false)
  const [speed, setSpeed] = useState(1)

  const frames = person.frames
  const frame: ReplayFrame | undefined = frames[at]
  const scale = frame?.shot ? width / frame.shot.w : 1
  const stageH = frame ? Math.round((frame.viewport.h || 800) * scale) : 360

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

  // 화면이 바뀌는 지점. 진행 막대에 눈금으로 찍어 "여기서 넘어갔다"를 보여준다.
  const marks = useMemo(
    () =>
      frames
        .map((f, i) => (i > 0 && f.screen !== frames[i - 1].screen ? i : -1))
        .filter((i) => i >= 0),
    [frames],
  )

  const done = person.outcome === 'success'
  const label = usePersonaLabel()

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <div className="flex items-center gap-[10px] border-b border-line bg-main/[0.06] px-[18px] py-[10px]">
        <PersonaFace id={person.id} size={28} />
        <span className="text-[14px] font-bold text-heading">
          {label(person.id)} 여정 재생
        </span>
        <span
          className={`rounded-[6px] px-[7px] py-[2px] text-[11px] font-bold text-white ${
            done ? 'bg-[#00824f]' : 'bg-[#df2d48]'
          }`}
        >
          {done ? '🏆' : '⚑'} {person.end_label}
        </span>
        {person.synthetic ? (
          <span className="rounded-[6px] bg-[#fdf4e3] px-[7px] py-[2px] text-[11px] font-semibold text-[#9a6b1a]">
            추정 데이터
          </span>
        ) : null}
        <span className="truncate text-[12px] text-subtext">
          {person.age_band && person.gender
            ? `${person.age_band} · ${person.gender} · ${person.label}`
            : person.label}
        </span>
        {onExit ? (
          <button
            type="button"
            onClick={onExit}
            className="ml-auto shrink-0 rounded-[8px] border border-line bg-white px-[10px] py-[4px] text-[12px] font-semibold text-heading hover:bg-black/[0.03]"
          >
            ← 이 단계로 돌아가기
          </button>
        ) : null}
      </div>

      <div className="flex flex-1 items-center justify-center overflow-auto bg-[#f6f7f9] p-[16px]">
        {frame?.shot ? (
          <div
            className="relative shrink-0 overflow-hidden rounded-[8px] border border-line bg-white"
            style={{ width, height: stageH }}
          >
            {/* 사진을 그 스텝의 스크롤 위치로 민다. 사람이 그때 본 화면이다. */}
            <img
              src={frame.shot.src}
              alt=""
              className="absolute left-0 max-w-none transition-[top] duration-500"
              style={{ width, top: -Math.round(frame.scroll_y * scale) }}
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
                  boxShadow: '0 0 0 9999px rgba(0,0,0,0.18)',
                }}
              />
            ) : null}
          </div>
        ) : (
          <p className="py-[60px] text-center text-[14px] text-subtext">
            이 화면은 답사자가 찍어둔 사진이 없어요.
          </p>
        )}
      </div>

      {/* 속마음 — 이 무대의 알맹이다. 화면보다 이게 먼저 읽혀야 한다. */}
      <div className="border-t border-line px-[18px] py-[12px]">
        <p className="flex flex-wrap items-center gap-[8px] text-[12px] text-subtext">
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
        <blockquote className="mt-[6px] rounded-[10px] border border-main/30 bg-white px-[13px] py-[10px] text-[13px] leading-[1.6] text-body">
          “{frame?.thought}”
        </blockquote>
      </div>

      <div className="flex items-center gap-[10px] border-t border-line px-[18px] py-[10px]">
        <button
          type="button"
          onClick={() => {
            if (at >= frames.length - 1) setAt(0)
            setPlaying((v) => !v)
          }}
          className="h-[30px] shrink-0 rounded-[8px] bg-main px-[12px] text-[12px] font-semibold text-white"
        >
          {playing ? '❚❚ 멈춤' : at >= frames.length - 1 ? '↻ 다시' : '▶ 재생'}
        </button>
        <div className="flex shrink-0 rounded-[8px] border border-line p-[2px]">
          {SPEEDS.map((s, i) => (
            <button
              key={s.label}
              type="button"
              onClick={() => setSpeed(i)}
              className={`rounded-[6px] px-[7px] py-[2px] text-[11px] font-semibold ${
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
  )
}
