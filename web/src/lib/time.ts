/** ISO 타임스탬프를 "2시간 전" 같은 문구로. 디자인이 쓰는 표기를 그대로 맞춘다. */
export function timeAgo(iso: string): string {
  const then = new Date(iso).getTime()
  if (Number.isNaN(then)) return ''

  const seconds = Math.max(0, (Date.now() - then) / 1000)
  if (seconds < 60) return '방금 전'

  const minutes = Math.floor(seconds / 60)
  if (minutes < 60) return `${minutes}분 전`

  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `${hours}시간 전`

  const days = Math.floor(hours / 24)
  if (days < 30) return `${days}일 전`

  const months = Math.floor(days / 30)
  if (months < 12) return `${months}달 전`

  return `${Math.floor(months / 12)}년 전`
}
