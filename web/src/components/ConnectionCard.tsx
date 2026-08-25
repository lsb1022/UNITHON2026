import checkIcon from '../assets/icons/check-filled.svg'
import playIcon from '../assets/icons/play.svg'
import type { ConnectivityResult } from '../api/client'

export type ConnectionState =
  | { status: 'idle' }
  | { status: 'checking' }
  | { status: 'done'; result: ConnectivityResult }
  | { status: 'failed'; message: string }

/** 오류 종류별 다음 행동. "실패했어요"만 적으면 사용자가 뭘 고쳐야 할지 모른다. */
const HINTS: Record<string, string> = {
  dns: '도메인 철자와 .com / .co.kr 을 확인해 주세요.',
  refused: '서버가 켜져 있는지, 방화벽이 막고 있지 않은지 확인해 주세요.',
  timeout: '사이트가 응답하지 않아요. 잠시 뒤 다시 시도해 주세요.',
  http_error: '주소는 살아 있지만 해당 경로가 없어요. 경로를 확인해 주세요.',
  invalid: '주소 형식이 올바르지 않아요.',
  empty: '주소를 입력해 주세요.',
  transport: '네트워크 문제로 연결하지 못했어요.',
}

export function ConnectionCard({
  state,
  onPreview,
  onRetry,
}: {
  state: ConnectionState
  onPreview: () => void
  onRetry: () => void
}) {
  if (state.status === 'idle') return null

  if (state.status === 'checking') {
    return (
      <Shell>
        <div className="flex items-center gap-[16px]">
          <span className="grid size-[48px] shrink-0 place-items-center rounded-[12px] bg-main-soft">
            <span className="size-[20px] animate-spin rounded-full border-2 border-main border-t-transparent" />
          </span>
          <div className="flex flex-col gap-[6px]">
            <p className="text-[18px] leading-[1.45] font-bold text-heading">
              연결을 확인하고 있어요
            </p>
            <p className="text-[14px] leading-[1.45] text-body">
              주소를 직접 열어 응답과 화면 구조를 살펴보는 중이에요.
            </p>
          </div>
        </div>
      </Shell>
    )
  }

  if (state.status === 'failed' || (state.status === 'done' && !state.result.ok)) {
    const result = state.status === 'done' ? state.result : null
    const message = state.status === 'failed' ? state.message : state.result.message
    const hint = result?.error_kind ? HINTS[result.error_kind] : undefined

    return (
      <Shell tone="danger">
        {/* 오른쪽 버튼은 카드 높이 기준 세로 중앙에 둔다 (설명 줄 수가 상태마다 달라진다) */}
        <div className="flex items-center justify-between gap-[20px]">
          <div className="flex gap-[16px]">
            <span className="grid size-[48px] shrink-0 place-items-center rounded-[12px] bg-danger-soft">
              <ExclamationMark />
            </span>
            <div className="flex flex-col gap-[8px]">
              <p className="text-[18px] leading-[1.45] font-bold text-danger">연결할 수 없어요</p>
              <p className="text-[14px] leading-[1.45] text-body">{message}</p>
              {hint ? <p className="text-[13px] leading-[1.45] text-subtext">{hint}</p> : null}
              <div className="mt-[3px] flex flex-wrap gap-[10px]">
                {result?.status ? <Badge tone="danger">HTTP {result.status}</Badge> : null}
                {result?.error_kind ? <Badge tone="danger">{result.error_kind}</Badge> : null}
              </div>
            </div>
          </div>

          <button
            type="button"
            onClick={onRetry}
            className="mr-[19px] h-[44px] shrink-0 rounded-[12px] border border-line bg-white px-[18px] text-[15px] font-semibold text-heading transition-colors hover:bg-black/[0.03]"
          >
            다시 시도
          </button>
        </div>
      </Shell>
    )
  }

  const { result } = state
  const description = [
    result.link_count ? `링크 ${result.link_count}개를 확인했어요.` : '응답을 확인했어요.',
    result.title ? `“${result.title}”` : null,
  ]
    .filter(Boolean)
    .join(' ')

  return (
    <Shell>
      <div className="flex items-center justify-between gap-[20px]">
        <div className="flex gap-[16px]">
          <span className="grid size-[48px] shrink-0 place-items-center rounded-[12px] bg-success-soft">
            <img src={checkIcon} alt="" aria-hidden className="size-[24px]" />
          </span>
          <div className="flex flex-col gap-[10px]">
            <p className="text-[18px] leading-[1.45] font-bold text-heading">연결할 수 있어요</p>
            <p className="text-[14px] leading-[1.45] text-body">{description}</p>
            <div className="mt-[3px] flex flex-wrap gap-[10px]">
              <Badge>접근 가능</Badge>
              {result.status ? <Badge>HTTP {result.status}</Badge> : null}
              {/* 임베드 가능 여부는 도달 가능 여부와 다른 사실이다. 섞어서 적지 않는다.
                  브라우저에서는 열어보기 전에 알 수 없으므로, 모를 때는
                  모른다고 적는다 — 가능하다고 해놓고 안 되면 고장으로 읽힌다. */}
              {result.embeddable === true ? (
                <Badge>미리보기 가능</Badge>
              ) : result.embeddable === false ? (
                <Badge tone="muted">미리보기 차단됨</Badge>
              ) : (
                <Badge tone="muted">미리보기는 열어봐야 알 수 있어요</Badge>
              )}
            </div>
          </div>
        </div>

        <button
          type="button"
          onClick={onPreview}
          // Figma(109:7654): 카드 오른쪽 끝에서 42px 안쪽. 패딩 23px + 19px.
          className="mr-[19px] flex w-[58px] shrink-0 flex-col items-center gap-[6px]"
        >
          <img src={playIcon} alt="" aria-hidden className="size-[42px] rotate-90" />
          <span className="text-[14px] leading-[1.45] font-medium text-heading">미리보기</span>
        </button>
      </div>
    </Shell>
  )
}

function Shell({
  children,
  tone = 'default',
}: {
  children: React.ReactNode
  tone?: 'default' | 'danger'
}) {
  return (
    <div
      className={`w-full max-w-[1280px] rounded-[20px] border bg-white p-[23px] ${
        tone === 'danger' ? 'border-danger/40' : 'border-line'
      }`}
    >
      {children}
    </div>
  )
}

const BADGE_TONE = {
  success: 'bg-success-bg text-success',
  danger: 'bg-danger-bg text-danger',
  muted: 'bg-track text-body',
} as const

function Badge({
  children,
  tone = 'success',
}: {
  children: React.ReactNode
  tone?: keyof typeof BADGE_TONE
}) {
  return (
    <span
      className={`rounded-[15px] px-[21px] py-[5px] font-noto text-[13px] font-medium ${BADGE_TONE[tone]}`}
    >
      {children}
    </span>
  )
}

/** 실패 아이콘은 Figma에 없어 텍스트 글리프로 대신한다 (벡터를 임의로 그리지 않는다). */
function ExclamationMark() {
  return (
    <span aria-hidden className="text-[22px] leading-none font-bold text-danger">
      !
    </span>
  )
}
