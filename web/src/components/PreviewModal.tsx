import { useEffect, useState } from 'react'
import { knownShot } from '../lib/siteShots'

type PreviewModalProps = {
  open: boolean
  onClose: () => void
  /** 실제로 띄울 주소. 서버가 정규화한 final_url 을 넘기는 것이 안전하다. */
  url: string | null
  /** 서버가 판정한 임베드 가능 여부. false면 iframe이 빈 화면으로 뜨므로 미리 안내한다. */
  embeddable: boolean
  blockReason?: string | null
}

export function PreviewModal({
  open,
  onClose,
  url,
  embeddable,
  blockReason,
}: PreviewModalProps) {
  const [loaded, setLoaded] = useState(false)
  /** iframe 이 제때 안 뜨면 찍어 둔 사진으로 넘어간다. */
  const [timedOut, setTimedOut] = useState(false)

  useEffect(() => {
    if (!open) return
    setLoaded(false)
    setTimedOut(false)

    // 프레임이 막히면 브라우저가 오류를 주지 않는다. 빈 화면인 채로 load 만 나거나
    // 아무 일도 일어나지 않는다. 그래서 시간으로 판단한다 — 이만큼 기다려도
    // 안 뜨면 안 뜨는 것으로 본다.
    const timer = window.setTimeout(() => setTimedOut(true), FRAME_WAIT_MS)

    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', onKeyDown)
    return () => {
      window.clearTimeout(timer)
      window.removeEventListener('keydown', onKeyDown)
    }
  }, [open, onClose, url])

  if (!open || !url) return null

  const shot = knownShot(url)

  return (
    <div
      role="dialog"
      aria-modal
      aria-label="연결한 화면 미리보기"
      onClick={onClose}
      className="fixed inset-0 z-50 grid place-items-center bg-black/40 p-[32px]"
    >
      <div
        onClick={(event) => event.stopPropagation()}
        className="relative h-[620px] max-h-full w-[900px] max-w-full overflow-hidden rounded-[16px] bg-white shadow-[0_20px_60px_rgba(0,0,0,0.25)]"
      >
        {/* 닫기 버튼만 모달 밖(어두운 배경 위)에 띄운다. 화면 자체를 가리지 않는다. */}
        <button
          type="button"
          onClick={onClose}
          aria-label="미리보기 닫기"
          className="absolute -top-[42px] right-0 z-10 flex items-center gap-[6px] text-[14px] font-medium text-white/90 transition-colors hover:text-white"
        >
          닫기 <span className="text-[18px] leading-none">×</span>
        </button>

        <div className="relative size-full bg-white">
          {/* 진짜 화면을 띄우는 것이 먼저다. 못 띄우면 그 주소를 실제로 열어
              찍어 둔 사진으로, 그것도 없으면 막혔다는 안내로 내려간다. */}
          {embeddable && !(timedOut && !loaded) ? (
            <>
              {!loaded ? (
                <div className="absolute inset-0 grid place-items-center">
                  <span className="size-[28px] animate-spin rounded-full border-2 border-main border-t-transparent" />
                </div>
              ) : null}
              <iframe
                title="연결한 화면 미리보기"
                src={url}
                onLoad={() => setLoaded(true)}
                // 남의 사이트를 우리 페이지 안에서 여는 것이므로 권한을 최소로 준다.
                sandbox="allow-scripts allow-same-origin allow-forms allow-popups"
                referrerPolicy="no-referrer"
                className="size-full border-0"
              />
            </>
          ) : shot ? (
            <ShotPreview url={url} shot={shot} />
          ) : (
            <BlockedNotice url={url} reason={blockReason} />
          )}
        </div>
      </div>
    </div>
  )
}

/** 얼마를 기다렸다가 사진으로 넘어갈지. 느린 사이트도 이 안에는 첫 화면이 뜬다. */
const FRAME_WAIT_MS = 4000

/**
 * 찍어 둔 첫 화면. 살아 있는 화면이 아니라는 것을 숨기지 않고 말한다 —
 * 스크롤도 클릭도 안 되는 그림을 진짜 화면인 척 두면 눌러보다 고장으로 읽는다.
 */
function ShotPreview({ url, shot }: { url: string; shot: string }) {
  return (
    <div className="flex h-full flex-col">
      <div className="min-h-0 flex-1 overflow-y-auto bg-track">
        <img src={shot} alt="연결한 화면의 첫 화면" className="w-full" />
      </div>
      <div className="flex shrink-0 items-center justify-between gap-[16px] border-t border-divider px-[20px] py-[14px]">
        <p className="text-[13px] text-body">
          이 창에서는 사이트를 직접 열지 못해서 <b className="font-semibold">찍어 둔 첫 화면</b>을
          보여주고 있어요. 연결 자체는 정상이에요.
        </p>
        <a
          href={url}
          target="_blank"
          rel="noreferrer noopener"
          className="shrink-0 rounded-[10px] bg-main px-[16px] py-[9px] text-[14px] font-semibold text-white hover:bg-[#2872dd]"
        >
          새 탭에서 열기
        </a>
      </div>
    </div>
  )
}

function BlockedNotice({ url, reason }: { url: string; reason?: string | null }) {
  return (
    <div className="grid h-full place-items-center px-[40px] text-center">
      <div className="flex max-w-[420px] flex-col items-center gap-[12px]">
        <span className="grid size-[48px] place-items-center rounded-[12px] bg-track text-[22px]">
          🔒
        </span>
        <p className="text-[18px] font-bold text-heading">이 사이트는 미리보기를 막아 뒀어요</p>
        <p className="text-[14px] leading-[1.6] text-body">
          사이트가 다른 페이지 안에 표시되는 것을 차단하고 있어요. 연결 자체는 정상이라 테스트는
          그대로 진행할 수 있어요.
        </p>
        {reason ? (
          <code className="rounded-[8px] bg-track px-[12px] py-[6px] text-[12px] text-subtext">
            {reason}
          </code>
        ) : null}
        <a
          href={url}
          target="_blank"
          rel="noreferrer noopener"
          className="mt-[6px] rounded-[12px] bg-main px-[20px] py-[10px] text-[15px] font-semibold text-white hover:bg-[#2872dd]"
        >
          새 탭에서 열기
        </a>
      </div>
    </div>
  )
}
