import { useRef, useState, type DragEvent } from 'react'
import folderFilledIcon from '../assets/icons/folder-filled.svg'

type FileDropZoneProps = {
  file: File | null
  onSelect: (file: File | null) => void
  accept?: string
  placeholder?: string
  /** 최대 크기(MB). 넘으면 선택되지 않고 이유를 보여준다. */
  maxSizeMb?: number
}

export function FileDropZone({
  file,
  onSelect,
  accept = '.xml,.json,.md,.txt,.csv',
  placeholder = 'sitemap.xml, readme.md …',
  maxSizeMb = 10,
}: FileDropZoneProps) {
  const inputRef = useRef<HTMLInputElement>(null)
  const [dragging, setDragging] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const accepted = accept.split(',').map((ext) => ext.trim().toLowerCase())

  const take = (next: File | null) => {
    setError(null)
    if (!next) {
      onSelect(null)
      return
    }
    const ext = `.${next.name.split('.').pop()?.toLowerCase() ?? ''}`
    if (!accepted.includes(ext)) {
      setError(`${ext} 형식은 받을 수 없어요. ${accept} 만 올릴 수 있어요.`)
      return
    }
    if (next.size > maxSizeMb * 1024 * 1024) {
      setError(`파일이 ${maxSizeMb}MB를 넘어요.`)
      return
    }
    onSelect(next)
  }

  const onDrop = (event: DragEvent<HTMLDivElement>) => {
    event.preventDefault()
    setDragging(false)
    take(event.dataTransfer.files?.[0] ?? null)
  }

  return (
    <div className="flex w-full max-w-[1280px] flex-col gap-[8px]">
      <div
        onDragOver={(event) => {
          event.preventDefault()
          setDragging(true)
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
        className={`flex min-h-[62px] w-full items-center gap-[12px] rounded-[16px] border border-dashed px-[17px] py-[12px] transition-colors ${
          dragging ? 'border-main bg-main-soft' : 'border-line bg-white'
        }`}
      >
        <img src={folderFilledIcon} alt="" aria-hidden className="size-[24px]" />

        {file ? (
          <>
            <span className="min-w-0 flex-1 truncate text-[15px] text-ink">{file.name}</span>
            <span className="shrink-0 text-[13px] text-subtext">{formatSize(file.size)}</span>
            <button
              type="button"
              onClick={() => take(null)}
              className="shrink-0 rounded-[10px] px-[10px] py-[6px] text-[13px] font-medium text-subtext hover:bg-black/[0.05]"
            >
              제거
            </button>
          </>
        ) : (
          <>
            <span className="min-w-0 flex-1 truncate text-[15px] text-placeholder">
              {placeholder}
            </span>
          </>
        )}

        <button
          type="button"
          onClick={() => inputRef.current?.click()}
          className="h-[42px] shrink-0 rounded-[12px] bg-subtext/40 px-[20px] text-[15px] leading-[1.45] font-bold text-white transition-colors hover:bg-subtext/55"
        >
          {file ? '변경' : '업로드'}
        </button>

        <input
          ref={inputRef}
          type="file"
          accept={accept}
          className="hidden"
          onChange={(event) => take(event.target.files?.[0] ?? null)}
        />
      </div>

      {error ? <p className="text-[13px] text-danger">{error}</p> : null}
    </div>
  )
}

function formatSize(bytes: number) {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} KB`
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`
}
