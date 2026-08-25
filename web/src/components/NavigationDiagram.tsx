import { useMemo, useRef, useState } from 'react'
import type { DiagramNode, DiagramPayload } from '../api/client'

/**
 * 네비게이션 다이어그램 뷰 (Figma 276:3101 / 276:3259).
 *
 * 세로 막대 하나가 '어떤 단계의 어떤 화면', 그 사이를 잇는 띠가 '그 화면에서
 * 다음 화면으로 넘어간 인원'이다. 막대 높이와 띠 두께는 같은 눈금(인원 1명 = unit px)을
 * 쓴다 — 눈금을 따로 잡으면 "굵은 띠가 얇은 막대로 들어가는" 그림이 나온다.
 *
 * 색은 결과를 따른다: 그 마디를 지난 사람 중 이탈이 더 많으면 빨강, 아니면 초록
 * (Figma 276:3213 범례 · 성공 #00824f · 실패 #df2d48).
 */

const COLUMN_GAP = 190
const NODE_WIDTH = 8
const NODE_GAP = 14
const PLOT_HEIGHT = 560
const TOP = 56
const LEFT = 40
/** 인원이 0에 가까운 마디도 선으로는 보여야 한다. */
const MIN_THICKNESS = 3

const SUCCESS = '#00824f'
const FAIL = '#df2d48'

type Placed = DiagramNode & { x: number; y: number; height: number }

type Hover = { label: string; count: number; percent: number; failing: boolean; x: number; y: number }

export function NavigationDiagram({ data }: { data: DiagramPayload }) {
  const [hover, setHover] = useState<Hover | null>(null)
  const frame = useRef<HTMLDivElement>(null)

  const layout = useMemo(() => build(data), [data])

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
      <div className="overflow-x-auto pb-[10px]">
        <svg width={width} height={height} role="img" aria-label="네비게이션 다이어그램">
          {columns.map((column) => (
            <text
              key={column.index}
              x={column.x}
              y={28}
              className="fill-heading text-[15px] font-semibold"
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
              fillOpacity={hover?.label === ribbon.label ? 0.4 : 0.15}
              // mouseenter 한 번이 아니라 움직일 때마다 받는다. 띠가 겹쳐 있으면
              // enter 가 한 번도 안 오는 자리가 생기고, 그러면 말풍선이 아예 안 뜬다.
              onMouseMove={(event) => {
                const box = frame.current?.getBoundingClientRect()
                if (!box) return
                setHover({
                  label: ribbon.label,
                  count: ribbon.count,
                  percent: ribbon.percent,
                  failing: ribbon.failing,
                  x: event.clientX - box.left,
                  y: event.clientY - box.top,
                })
              }}
              onMouseLeave={() => setHover(null)}
            />
          ))}

          {nodes.map((node) => (
            <g key={node.id}>
              <rect
                x={node.x}
                y={node.y}
                width={NODE_WIDTH}
                height={node.height}
                rx={3}
                fill={node.drop > node.success ? FAIL : SUCCESS}
              />
              <foreignObject x={node.x + 14} y={node.y - 3} width={COLUMN_GAP - 40} height={24}>
                <span className="inline-block max-w-full truncate rounded-[6px] border border-line bg-white px-[6px] py-[2px] text-[11px] text-heading">
                  {node.title}
                </span>
              </foreignObject>
            </g>
          ))}
        </svg>
      </div>

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
            {hover.label}
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

function build(data: DiagramPayload) {
  const columns = data.columns.filter((column) => column.nodes.length > 0)
  if (columns.length === 0 || data.total === 0) return null

  const tallest = Math.max(...columns.map((c) => c.nodes.length))
  const unit = (PLOT_HEIGHT - NODE_GAP * (tallest - 1)) / data.total

  const placed = new Map<string, Placed>()
  for (const column of columns) {
    let y = TOP
    for (const node of column.nodes) {
      const height = Math.max(MIN_THICKNESS, node.count * unit)
      placed.set(node.id, { ...node, x: LEFT + column.index * COLUMN_GAP, y, height })
      y += height + NODE_GAP
    }
  }

  // 띠는 굵은 것부터 쌓는다. 그래야 얇은 띠가 굵은 띠에 가려 사라지지 않는다.
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
      label: `Step${from.column + 1} → Step${to.column + 1}`,
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
    columns: columns.map((column) => ({
      index: column.index,
      label: column.label,
      x: LEFT + column.index * COLUMN_GAP,
    })),
    width: LEFT * 2 + (columns.length - 1) * COLUMN_GAP + COLUMN_GAP,
    height: TOP + PLOT_HEIGHT + 40,
  }
}
