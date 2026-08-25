import { useMemo, useRef, useState } from 'react'
import type { DiagramNode, DiagramPayload } from '../api/client'

/**
 * 네비게이션 다이어그램 뷰 (Figma 276:3101 / 276:3259).
 *
 * **열 하나가 '몇 번째 스텝'이다.** 그 안의 세로 막대는 그 스텝에 어느 화면에
 * 있었는지, 막대를 잇는 띠는 다음 스텝에 어디로 갔는지다. 화면을 열로 세우면
 * 같은 화면에 세 번 들른 사람이 한 막대로 접혀 "붙잡혀 있었다"가 사라지는데,
 * 스텝을 열로 세우면 그 정체가 가로로 길게 드러난다.
 *
 * 막대 높이와 띠 두께는 같은 눈금(인원 1명 = unit px)을 쓴다 — 눈금을 따로
 * 잡으면 "굵은 띠가 얇은 막대로 들어가는" 그림이 나온다.
 *
 * 색은 결과를 따른다: 그 마디를 지난 사람 중 이탈이 더 많으면 빨강, 아니면 초록
 * (Figma 276:3213 범례 · 성공 #00824f · 실패 #df2d48).
 */

const NODE_WIDTH = 8
const NODE_GAP = 14
const PLOT_HEIGHT = 560
const TOP = 62
const LEFT = 40
/** 인원이 0에 가까운 마디도 선으로는 보여야 한다. */
const MIN_THICKNESS = 3

const SUCCESS = '#00824f'
const FAIL = '#df2d48'

/**
 * 스텝이 열이라 열이 스무 개를 넘을 수 있다. 넓은 간격을 그대로 쓰면 가로로만
 * 5000px 짜리 그림이 되어 아무도 끝까지 안 본다. 열이 많으면 좁혀서 시작한다.
 *
 * 시작값일 뿐이고, 보는 사람이 슬라이더로 바꾼다 — 좁히면 전체 흐름이 한눈에
 * 들어오고, 벌리면 한 구간의 갈림을 자세히 볼 수 있다. 둘 다 필요한 시야다.
 */
function defaultGap(count: number): number {
  if (count > 16) return 104
  if (count > 9) return 136
  return 190
}

/** 슬라이더가 움직일 수 있는 범위. 아래로는 막대가 겹치고 위로는 화면을 벗어난다. */
const GAP_MIN = 44
const GAP_MAX = 260

type Placed = DiagramNode & { x: number; y: number; height: number; label: boolean }

type Hover = {
  id: string
  title: string
  count: number
  percent: number
  failing: boolean
  x: number
  y: number
}

export function NavigationDiagram({
  data,
  onPickNode,
}: {
  data: DiagramPayload
  /** 막대를 누르면 그 단계의 상세 창을 열라는 신호. 띄는 그 출발 막대로 연결한다. */
  onPickNode?: (nodeId: string) => void
}) {
  const [hover, setHover] = useState<Hover | null>(null)
  const frame = useRef<HTMLDivElement>(null)

  const columnCount = data.columns.filter((c) => c.nodes.length > 0).length
  // null 이면 "아직 사람이 안 건드렸다" — 열 수에 맞춘 기본값을 쓴다.
  // 0 을 그 뜻으로 쓰면 슬라이더를 맨 왼쪽에 둔 것과 구별되지 않는다.
  const [gapOverride, setGapOverride] = useState<number | null>(null)
  const gap = gapOverride ?? defaultGap(columnCount)

  const layout = useMemo(() => build(data, gap), [data, gap])

  if (layout === null) {
    return (
      <p className="py-[80px] text-center text-[15px] text-subtext">
        아직 그릴 이동 기록이 없어요. 테스트를 한 번 돌리면 여기에 흐름이 나타나요.
      </p>
    )
  }

  const { nodes, ribbons, width, height, columns } = layout

  return (
    <div ref={frame} className="relative">
      <div className="mb-[12px] flex items-center gap-[12px]">
        <label
          htmlFor="diagram-gap"
          className="shrink-0 text-[13px] font-medium text-subtext"
        >
          단계 간격
        </label>
        <input
          id="diagram-gap"
          type="range"
          min={GAP_MIN}
          max={GAP_MAX}
          step={4}
          value={gap}
          onChange={(e) => setGapOverride(Number(e.target.value))}
          className="h-[4px] w-[220px] cursor-pointer accent-[var(--color-main)]"
        />
        <span className="w-[52px] shrink-0 text-[12px] text-subtext tabular-nums">
          {gap}px
        </span>
        {gapOverride === null ? (
          <span className="text-[12px] text-subtext">
            좁히면 전체가 한눈에, 벌리면 갈림이 또렷하게 보여요
          </span>
        ) : (
          <button
            type="button"
            onClick={() => setGapOverride(null)}
            className="text-[12px] text-main underline underline-offset-4"
          >
            기본값으로
          </button>
        )}
      </div>

      <div className="overflow-x-auto pb-[10px]">
        <svg width={width} height={height} role="img" aria-label="네비게이션 다이어그램">
          {columns.map((column) => (
            <text
              key={column.index}
              x={column.x}
              y={30}
              className="fill-heading text-[16px] font-bold tabular-nums"
            >
              {column.label}
            </text>
          ))}

          {/* 띠를 먼저 그려야 막대가 그 위에 올라온다. */}
          {ribbons.map((ribbon) => (
            <path
              key={ribbon.id}
              d={ribbon.d}
              fill={ribbon.failing ? FAIL : SUCCESS}
              fillOpacity={hover?.id === ribbon.id ? 0.4 : 0.15}
              // mouseenter 한 번이 아니라 움직일 때마다 받는다. 띠가 겹쳐 있으면
              // enter 가 한 번도 안 오는 자리가 생기고, 그러면 말풍선이 아예 안 뜬다.
              onMouseMove={(event) => {
                const box = frame.current?.getBoundingClientRect()
                if (!box) return
                setHover({
                  id: ribbon.id,
                  title: ribbon.label,
                  count: ribbon.count,
                  percent: ribbon.percent,
                  failing: ribbon.failing,
                  x: event.clientX - box.left,
                  y: event.clientY - box.top,
                })
              }}
              onMouseLeave={() => setHover(null)}
              onClick={() => onPickNode?.(ribbon.source)}
              style={onPickNode ? { cursor: 'pointer' } : undefined}
            />
          ))}

          {nodes.map((node) => {
            // 여정의 끝. 이 막대들이 이 그림의 결론이라 다른 것보다 굵고 진하게,
            // 이름표도 색을 채워 멀리서도 어디서 끝났는지 먼저 보이게 한다.
            const done = node.key === 'end_goal'
            const left = node.key === 'end_drop'
            const terminal = done || left
            const color = node.drop > node.success ? FAIL : SUCCESS
            const width = terminal ? NODE_WIDTH + 6 : NODE_WIDTH

            return (
              <g
                key={node.id}
                onClick={() => onPickNode?.(node.id)}
                style={onPickNode ? { cursor: 'pointer' } : undefined}
              >
                {/* 막대가 얇아 그것만으로는 짚기 어렵다. 더 넓은 투명 판을 덮는다. */}
                <rect
                  x={node.x - 6}
                  y={node.y}
                  width={width + 12}
                  height={node.height}
                  fill="transparent"
                />
                {terminal ? (
                  // 끝 막대에는 옅은 후광을 둘러 시선이 먼저 닿게 한다.
                  <rect
                    x={node.x - 4}
                    y={node.y - 4}
                    width={width + 8}
                    height={node.height + 8}
                    rx={7}
                    fill={color}
                    fillOpacity={0.16}
                  />
                ) : null}
                <rect
                  x={node.x}
                  y={node.y}
                  width={width}
                  height={node.height}
                  rx={terminal ? 5 : 3}
                  fill={color}
                />
                {/* 같은 화면이 여러 열에 이어지면 이름은 처음 한 번만 붙인다.
                    열마다 붙이면 25열 × 화면 이름이 그림을 덮는다. */}
                {node.label ? (
                  <foreignObject
                    x={node.x + width + 6}
                    y={node.y - 5}
                    width={Math.max(64, gap - 20)}
                    height={28}
                  >
                    <span
                      className={
                        terminal
                          ? 'inline-flex max-w-full items-center gap-[3px] truncate rounded-[7px] px-[8px] py-[3px] text-[13px] font-bold text-white shadow-[0_1px_3px_rgba(0,0,0,0.18)]'
                          : 'inline-block max-w-full truncate rounded-[6px] border border-line bg-white px-[7px] py-[2px] text-[12px] text-heading'
                      }
                      style={terminal ? { backgroundColor: color } : undefined}
                    >
                      {done ? '🏆 ' : left ? '⚑ ' : ''}
                      {node.title}
                      {terminal ? ` ${node.count}` : ''}
                    </span>
                  </foreignObject>
                ) : null}
              </g>
            )
          })}
        </svg>
      </div>

      <p className="mt-[8px] text-[13px] text-subtext">
        열 하나가 한 스텝이에요. 여정이 끝난 사람은 굵은 막대
        {' '}<span className="rounded-[5px] bg-[#00824f] px-[6px] py-[1px] text-[12px] font-bold text-white">🏆 달성</span>
        {' · '}
        <span className="rounded-[5px] bg-[#df2d48] px-[6px] py-[1px] text-[12px] font-bold text-white">⚑ 이탈</span>
        {' '}로 빠집니다.
        {onPickNode ? ' 막대나 띠를 누르면 그 순간의 화면과 속마음을 볼 수 있어요.' : ''}
        {data.truncated ? (
          <>
            {' '}
            {data.max_columns}스텝을 넘긴 {data.truncated}명은 여기까지만 그렸어요.
          </>
        ) : null}
      </p>

      {hover ? (
        <div
          className="pointer-events-none absolute z-10 rounded-[10px] border border-line bg-white px-[16px] py-[12px] shadow-[0_6px_20px_rgba(0,0,0,0.08)]"
          style={{ left: hover.x + 16, top: hover.y + 16 }}
        >
          <p className="flex items-center gap-[8px] text-[15px] font-bold text-heading">
            <span
              className="size-[12px] rounded-[3px]"
              style={{ backgroundColor: hover.failing ? FAIL : SUCCESS }}
            />
            {hover.title}
          </p>
          <p className="mt-[4px] text-[13px] text-subtext">
            {hover.count} of {data.total}{' '}
            <span className="text-body">({hover.percent}%)</span>
          </p>
        </div>
      ) : null}
    </div>
  )
}

function build(data: DiagramPayload, gap: number) {
  const columns = data.columns.filter((column) => column.nodes.length > 0)
  if (columns.length === 0 || data.total === 0) return null

  const tallest = Math.max(...columns.map((c) => c.nodes.length))
  const unit = (PLOT_HEIGHT - NODE_GAP * (tallest - 1)) / data.total

  // 앞 열에 같은 화면이 없을 때만 이름표를 단다 — 새로 등장하는 화면만 소개한다.
  const previousKeys = new Map<number, Set<string>>()
  columns.forEach((_, i) => {
    previousKeys.set(i, new Set(columns[i - 1]?.nodes.map((n) => n.key) ?? []))
  })

  const placed = new Map<string, Placed>()
  columns.forEach((column, i) => {
    let y = TOP
    for (const node of column.nodes) {
      const height = Math.max(MIN_THICKNESS, node.count * unit)
      placed.set(node.id, {
        ...node,
        x: LEFT + i * gap,
        y,
        height,
        label: !previousKeys.get(i)?.has(node.key),
      })
      y += height + NODE_GAP
    }
  })

  const outCursor = new Map<string, number>()
  const inCursor = new Map<string, number>()
  const ribbons = []

  for (const link of data.links) {
    const from = placed.get(link.source)
    const to = placed.get(link.target)
    if (!from || !to) continue

    const thickness = Math.max(MIN_THICKNESS, link.count * unit)
    const y0 = from.y + (outCursor.get(from.id) ?? 0)
    const y1 = to.y + (inCursor.get(to.id) ?? 0)
    outCursor.set(from.id, (outCursor.get(from.id) ?? 0) + thickness)
    inCursor.set(to.id, (inCursor.get(to.id) ?? 0) + thickness)

    const x0 = from.x + NODE_WIDTH
    const x1 = to.x
    const mid = (x0 + x1) / 2

    ribbons.push({
      id: `${link.source}->${link.target}`,
      source: link.source,
      label: `${from.column + 1}단계 ${from.title} → ${to.title}`,
      count: link.count,
      percent: Math.round((100 * link.count) / data.total),
      failing: link.drop > link.success,
      d:
        `M ${x0} ${y0} C ${mid} ${y0}, ${mid} ${y1}, ${x1} ${y1} ` +
        `L ${x1} ${y1 + thickness} C ${mid} ${y1 + thickness}, ${mid} ${y0 + thickness}, ${x0} ${y0 + thickness} Z`,
    })
  }

  const nodes = [...placed.values()]
  return {
    nodes,
    ribbons,
    columns: columns.map((column, i) => ({
      index: column.index,
      label: column.label,
      x: LEFT + i * gap,
    })),
    width: LEFT * 2 + (columns.length - 1) * gap + gap,
    height: TOP + PLOT_HEIGHT + 40,
  }
}
