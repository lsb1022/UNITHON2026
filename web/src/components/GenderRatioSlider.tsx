const TRACK_W = 470

/**
 * 성별 비율 슬라이더 (Figma 130:13923).
 *
 * 왼쪽으로 갈수록 여성, 오른쪽으로 갈수록 남성. 값은 "여성 비율(0~100)"이다.
 * 트랙 양쪽 색을 각각 32% 투명도로 깔고 그 위에 흰 썸을 얹는다.
 *
 * 네이티브 <input type="range">를 쓰되 시각 요소는 전부 커스텀으로 그린다 —
 * 키보드 조작과 접근성 트리를 공짜로 얻기 위해서다.
 */
export function GenderRatioSlider({
  femalePercent,
  onChange,
  disabled = false,
  label,
}: {
  femalePercent: number
  onChange: (femalePercent: number) => void
  disabled?: boolean
  label: string
}) {
  const ratio = Math.min(100, Math.max(0, femalePercent)) / 100

  return (
    <div
      // 디자인 기준 폭은 470px 이지만, 좁은 화면에서는 남는 만큼만 쓴다.
      className={`relative h-[58px] w-full ${
        disabled ? 'pointer-events-none opacity-24 blur-[2px]' : ''
      }`}
      style={{ maxWidth: TRACK_W }}
    >
      <p className="absolute top-0 left-0 font-noto text-[13px] font-medium text-[#6b5ce7]">
        여성 {Math.round(femalePercent)}%
      </p>
      <p className="absolute top-0 right-0 font-noto text-[13px] font-medium text-main">
        남성 {100 - Math.round(femalePercent)}%
      </p>

      <div className="absolute top-[34px] right-0 left-0 h-[8px] rounded-[4px] bg-track">
        <div
          className="absolute inset-y-0 left-0 rounded-[4px] bg-[#6b5ce7] opacity-32"
          style={{ width: `${ratio * 100}%` }}
        />
        <div
          className="absolute inset-y-0 right-0 rounded-[4px] bg-main opacity-32"
          style={{ width: `${(1 - ratio) * 100}%` }}
        />
      </div>

      <input
        type="range"
        min={0}
        max={100}
        step={5}
        value={Math.round(femalePercent)}
        disabled={disabled}
        aria-label={label}
        onChange={(event) => onChange(Number(event.target.value))}
        className="ratio-slider absolute top-[28px] left-0 h-[20px] w-full cursor-pointer appearance-none bg-transparent"
      />
    </div>
  )
}

/** 상관없음 토글 (Figma 130:13930 / 130:14002) */
export function AgnosticToggle({
  active,
  onToggle,
  disabled = false,
  label,
}: {
  active: boolean
  onToggle: () => void
  disabled?: boolean
  label: string
}) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={active}
      aria-label={label}
      disabled={disabled}
      onClick={onToggle}
      // 150px 고정폭은 좁은 화면에서 슬라이더 자리를 잡아먹어 비율 표시를 밀어냈다.
      // 100px 로 줄이되 폭은 고정한다 — 켜고 끌 때마다 폭이 변하면 열이 행마다 어긋난다.
      className={`flex h-[34px] w-[100px] shrink-0 items-center justify-center gap-[4px] rounded-[17px] border font-noto text-[13px] font-medium whitespace-nowrap transition-colors disabled:cursor-not-allowed ${
        active
          ? 'border-main bg-main text-white'
          : 'border-line bg-white text-subtext hover:border-[#c2c2c2]'
      }`}
    >
      {/* 꺼졌을 때 자리만 비워두면 흰 배경에 안 보이는 체크가 있는 것처럼 글자가 밀린다.
          아예 빼서 글자를 가운데 두고, 켜졌을 때만 체크를 넣는다. 폭은 100px 로 고정이라
          체크가 들고 나도 열은 어긋나지 않는다. */}
      {active ? <CheckGlyph /> : null}
      상관없음
    </button>
  )
}

/** Figma가 내보낸 체크 패스 그대로 (12.49 × 8.95) */
function CheckGlyph({ className = '' }: { className?: string }) {
  return (
    <svg
      width="12.5"
      height="9"
      viewBox="0 0 12.4932 8.94616"
      fill="none"
      aria-hidden
      className={`shrink-0 ${className}`}
    >
      <path
        fillRule="evenodd"
        clipRule="evenodd"
        d="M12.2187 0.2748C12.3945 0.450607 12.4932 0.689021 12.4932 0.937612C12.4932 1.1862 12.3945 1.42462 12.2187 1.60042L5.14746 8.67168C4.97165 8.84743 4.73324 8.94616 4.48465 8.94616C4.23605 8.94616 3.99764 8.84743 3.82183 8.67168L0.286208 5.13605C0.196667 5.04957 0.125246 4.94612 0.0761127 4.83174C0.0269792 4.71736 0.0011171 4.59434 3.53968e-05 4.46986C-0.00104631 4.34538 0.0226741 4.22193 0.0698125 4.10672C0.116951 3.9915 0.186563 3.88683 0.274587 3.7988C0.362612 3.71078 0.467285 3.64117 0.582501 3.59403C0.697716 3.54689 0.821166 3.52317 0.945646 3.52425C1.07013 3.52533 1.19315 3.5512 1.30752 3.60033C1.4219 3.64946 1.52535 3.72088 1.61183 3.81042L4.48433 6.68292L10.8925 0.2748C10.9795 0.187681 11.0829 0.118572 11.1967 0.0714204C11.3105 0.024269 11.4324 0 11.5556 0C11.6787 0 11.8007 0.024269 11.9145 0.0714204C12.0283 0.118572 12.1316 0.187681 12.2187 0.2748Z"
        fill="currentColor"
      />
    </svg>
  )
}

/** 상관없음일 때 슬라이더 위를 덮는 안내 pill (Figma 130:14005) */
export function AgnosticNotice() {
  return (
    // 폭은 246px 이 기준이지만, 좁은 화면에서 두 줄로 깨지느니 내용에 맞춰 줄인다.
    <span className="pointer-events-none flex h-[34px] max-w-full items-center justify-center rounded-[17px] bg-track px-[18px] font-noto text-[13px] font-medium whitespace-nowrap text-body">
      성별 비율을 자동 배정해요
    </span>
  )
}

/** 슬라이더 값을 실제 인원수로 나눈다. 반올림 오차는 남성 쪽으로 흡수시킨다. */
export function splitByRatio(total: number, femalePercent: number) {
  const female = Math.round((total * femalePercent) / 100)
  return { female, male: total - female }
}

