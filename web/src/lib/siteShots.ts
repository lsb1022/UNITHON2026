import shotClean from '../assets/img/shot-clean.png'
import shotFlawed from '../assets/img/shot-flawed.png'
import shotWikipedia from '../assets/img/shot-wikipedia.png'

/**
 * 데모에 들어 있는 세 사이트의 첫 화면 사진.
 *
 * 사이트를 직접 여는 것이 정본이다 — 카드는 서버가 헤드리스 브라우저로 찍고,
 * 미리보기는 iframe 으로 진짜 화면을 띄운다. 다만 배포본에는 찍어 줄 서버가 없고,
 * iframe 은 상대 사이트 사정으로 빈 화면이 될 수 있다.
 *
 * 그때 기본 이미지로 떨어지면 세 프로젝트가 전부 똑같은 회색 판이 되어 어느 것이
 * 무엇인지 알 수 없다. 그래서 **우리가 아는 세 주소에 한해서만** 미리 찍어 둔 사진을
 * 쓴다. 지어낸 그림이 아니라 그 주소를 실제로 열어 찍은 화면이다.
 *
 * 모르는 주소는 null 이다 — 없는 것을 있는 척하지 않는다.
 */
export function knownShot(url: string | null | undefined): string | null {
  if (!url) return null
  if (url.startsWith('https://ko.wikipedia.org/')) return shotWikipedia
  if (url.includes('/ux-testbed/clean/')) return shotClean
  if (url.includes('/ux-testbed/flawed/')) return shotFlawed
  return null
}
