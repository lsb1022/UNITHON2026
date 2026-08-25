/**
 * 페르소나에게 사람 이름을 붙인다 — **화면에서만.**
 *
 * 우리 페르소나에는 이름도 나이도 성별도 없다. 특성 네 축(숙련도·주의 지속·
 * 인내심·탐색 범위)으로만 정의되고, 없는 값을 데이터에 지어 넣지 않는 것이
 * 이 프로젝트의 규칙이다.
 *
 * 그렇다고 P001·P002 만 늘어놓으면 사람 이야기로 안 읽힌다. "P002 가 포기했다"
 * 보다 "최지훈이 포기했다"가 회의실에서 훨씬 잘 전달된다. 반대로 데이터를 파는
 * 사람에게는 P002 가 편하다. 그래서 **보는 사람이 켜고 끈다.**
 *
 * 이름은 여기서 id 로부터 계산한다. 기록 파일에는 들어가지 않는다 — 데이터는
 * 여전히 이름이 없고, 이름은 화면이 붙인 딱지일 뿐이다. 같은 id 면 언제나
 * 같은 이름이 나오므로 실행을 다시 해도 사람이 바뀌지 않는다.
 */

/** 흔한 성 + 이름. 실존 인물을 가리키지 않도록 평범한 조합만 쓴다. */
const FAMILY = ['김', '이', '박', '최', '정', '강', '조', '윤', '장', '임', '한', '오']
const GIVEN = [
  '지훈', '서연', '민준', '수아', '도현', '하윤', '준서', '지우', '예준', '서윤',
  '시우', '하은', '주원', '다은', '건우', '지아', '현우', '수빈', '하준', '유진',
  '태윤', '채원', '민재', '나윤', '승우', '가은',
]

/** id 를 숫자로. 같은 id 면 언제나 같은 값이라 이름이 흔들리지 않는다. */
function seed(id: string): number {
  let h = 2166136261
  for (let i = 0; i < id.length; i++) {
    h ^= id.charCodeAt(i)
    h = Math.imul(h, 16777619)
  }
  return Math.abs(h)
}

/**
 * 이 id 에 붙일 이름.
 *
 * 성과 이름을 서로 다른 자리에서 뽑아, 앞 번호들이 같은 성으로 몰리지 않게 한다.
 */
export function personaName(id: string): string {
  const h = seed(id)
  return FAMILY[h % FAMILY.length] + GIVEN[Math.floor(h / FAMILY.length) % GIVEN.length]
}

const KEY = 'moji.personaNames'
/** 설정이 바뀌면 화면 전체가 같이 바뀌어야 한다. 창 안에서만 도는 신호. */
const EVENT = 'moji:persona-names'

export function namesOn(): boolean {
  try {
    return localStorage.getItem(KEY) === '1'
  } catch {
    // 사생활 보호 창처럼 저장이 막힌 곳. 기본값(끔)으로 돈다.
    return false
  }
}

export function setNamesOn(on: boolean): void {
  try {
    localStorage.setItem(KEY, on ? '1' : '0')
  } catch {
    // 저장은 못 해도 이번 화면에서는 바뀌어야 한다.
  }
  window.dispatchEvent(new CustomEvent(EVENT))
}

export function subscribeNames(fn: () => void): () => void {
  window.addEventListener(EVENT, fn)
  // 다른 탭에서 바꾼 것도 따라간다.
  window.addEventListener('storage', fn)
  return () => {
    window.removeEventListener(EVENT, fn)
    window.removeEventListener('storage', fn)
  }
}
