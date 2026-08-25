import { useEffect, useState } from 'react'
import { API_BASE } from '../api/client'
import placeholder from '../assets/img/placeholder-thumb.png'
import { knownShot } from '../lib/siteShots'

type Fit = 'top' | 'cover'

/**
 * 사이트 썸네일.
 *
 * 사이트를 처음 열었을 때의 화면 한 장을 보여준다. 진짜 이미지 한 장이다 —
 * 서버가 헤드리스 브라우저로 찍어 둔 PNG 를 <img> 로 받는다.
 *
 * 예전에는 iframe 을 축소해서 띄웠는데, 스크립트를 sandbox 로 막아도 CSS 애니메이션은
 * 그대로 돌아서 카드가 계속 움직였다. 캐러셀이 넘어가고 배너가 깜빡이는 카드가
 * 목록에 여러 장 뜨면 눈이 아프다. 이미지는 움직일 방법이 없다.
 *
 * 못 찍으면 **아는 사이트는 미리 찍어 둔 사진**으로, 모르는 사이트는 기본 이미지로
 * 떨어진다.
 *
 * fit:
 *   'top'   - 폭을 맞추고 위쪽을 보여준다 (가로 카드)
 *   'cover' - 정사각형 칸을 꽉 채우도록 확대해 가운데를 보여준다 (프로젝트 정보의 작은 칸)
 */
export function SitePreview({
  url,
  alt,
  fit = 'top',
}: {
  url: string | null
  alt: string
  fit?: Fit
}) {
  const [failed, setFailed] = useState(false)

  useEffect(() => {
    setFailed(false)
  }, [url])

  const objectPosition = fit === 'cover' ? 'object-center' : 'object-top'

  if (!url || failed) {
    const shot = url ? knownShot(url) : null
    return (
      <img
        src={shot ?? placeholder}
        alt={alt}
        // 기본 이미지는 비율이 달라서 잘라 채우면 로고가 잘린다. 사진일 때만 채운다.
        className={`size-full ${shot ? `object-cover ${objectPosition}` : 'object-cover'}`}
      />
    )
  }

  return (
    <img
      src={`${API_BASE}/api/thumbnail?url=${encodeURIComponent(url)}`}
      alt={alt}
      loading="lazy"
      decoding="async"
      onError={() => setFailed(true)}
      // 찍은 그림은 1280×800 가로 화면이다. 칸 비율이 어떻든 잘라서 채운다.
      // 가로 카드는 웹의 첫인상인 위쪽을, 정사각형 칸은 가운데를 보여준다.
      className={`size-full object-cover ${objectPosition}`}
    />
  )
}
