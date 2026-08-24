# MOJI STORE — UX 검증 테스트베드

AI가 웹사이트 UX를 검증해주는 서비스를 만들기에 앞서,
**우리 서비스가 실제로 뭘 잡아내는지 측정하기 위한 테스트 대상 사이트**입니다.

동일한 상품 데이터·URL 구조·구매 플로우 위에 쇼핑몰을 **두 벌** 만들었습니다.
바뀐 변수는 UI 품질 하나뿐입니다.

| 버전 | 경로 | 역할 |
|---|---|---|
| **CLEAN** | `clean/` | UX 베스트프랙티스를 지킨 기준선. 여기서 나온 지적 = **오탐(false positive)** |
| **FLAWED** | `flawed/` | 실무에서 자주 보이는 UX 결함 **68개**를 의도적으로 심은 버전 = **탐지 대상** |

- 정답지: [`DEFECTS.md`](DEFECTS.md) — 결함 68건의 ID·심각도·위치·탐지 방법
- 두 버전 대조 + 설계 이유: [`docs/comparison.html`](docs/comparison.html) (브라우저로 열어보세요)

---

## 왜 두 벌인가

결함만 있는 사이트 하나로 평가하면 **"많이 지적할수록 좋은 서비스"**가 되어버립니다.
화면마다 트집을 잡는 서비스가 만점을 받고, 정확한 서비스가 손해를 봅니다.

> **재현율은 결함판이, 정밀도는 정상판이 잽니다.**

실제 고객이 가장 먼저 불평하는 게 오탐이라, 정상판 쪽이 오히려 더 중요한 지표입니다.

---

## 실행

빌드 도구도 의존성도 없습니다. 정적 파일뿐입니다.

```bash
git clone https://github.com/lsb1022/UNITHON2026.git
cd UNITHON2026
python -m http.server 8000
```

- 런처(버전 선택 + 검증 시나리오): <http://localhost:8000/ux-testbed/>
- CLEAN: <http://localhost:8000/ux-testbed/clean/index.html>
- FLAWED: <http://localhost:8000/ux-testbed/flawed/index.html>

Node를 쓴다면 `npx serve -l 8000`도 동일합니다.

> `file://`로 열어도 대부분 동작하지만, 두 버전이 같은 `null` 오리진을 공유하고
> 크롤러의 URL 정규화가 달라질 수 있어 **HTTP 서버 사용을 권장**합니다.
> (장바구니 키는 `moji_cart_clean` / `moji_cart_flawed`로 분리돼 있어 서로 간섭하지 않습니다.)

---

## 구조

```
ux-testbed/
├── index.html            버전 선택 런처 + 검증 시나리오 10개
├── DEFECTS.md            정답지 68건
├── smoke-test.js         픽스처 자체 검증 (40개 항목)
├── docs/comparison.html  두 버전 대조 + 설계 이유
├── shared/
│   ├── products.js       두 버전이 공유하는 상품 12종
│   └── img/p1..p12.svg   상품 이미지 (외부 요청 없음)
├── clean/
│   ├── index.html  list.html  product.html
│   ├── cart.html   checkout.html  complete.html
│   └── assets/style.css  assets/app.js
└── flawed/
    └── (동일한 6개 페이지 + assets)
```

두 버전의 **페이지 구성·URL 구조·상품 데이터가 완전히 동일**합니다.
같은 크롤링 시나리오를 그대로 양쪽에 돌리고 결과만 빼면 됩니다.

---

## URL 맵 (양쪽 동일)

| 화면 | 경로 |
|---|---|
| 홈 | `index.html` |
| 상품 목록 | `list.html`, `list.html?cat=상의` |
| 상품 상세 | `product.html?id=1` … `?id=12` |
| 장바구니 | `cart.html` |
| 주문/결제 | `checkout.html` |
| 주문 완료 | `complete.html` |

- 품절 상품: `?id=7` (워시드 후디), `?id=12` (레더 벨트)
- 없는 상품: `?id=999` — 오류 처리 비교용
- 결과 0건 필터: 목록에서 **세일** 칩 (flawed 전용)

---

## 검증 시나리오

두 버전에 **똑같이** 적용하고 결과를 비교하세요.

1. 홈 → 카테고리 필터 → 상품 상세 진입
2. 색상·사이즈 선택 후 장바구니 담기 — **결과 피드백이 있는가?**
3. 장바구니에서 수량 변경 · 항목 삭제 — **되돌릴 수 있는가?**
4. 결제 화면에서 빈 값으로 제출 — **무엇이 잘못됐는지 알려주는가?**
5. 정상 입력 후 결제 → 주문 완료 — **총액이 앞 단계와 일치하는가?**
6. 품절 상품 담기 시도 (`?id=7`)
7. 없는 상품 ID 접근 (`?id=999`)
8. 375px 폭 모바일 뷰포트로 1~7 재실행
9. 마우스 없이 **Tab 키만으로** 결제까지 완주 시도
10. 페이지 로드 후 **10초 이상 체류** — flawed에만 팝업이 뜬다

---

## 채점

```
Recall    = 결함판에서 찾아낸 결함 수 / 68
Precision = 실제 결함 지적 수 / 전체 지적 수
FP rate   = 정상판에서의 지적 수 / 정상판 페이지 수 (6)
```

심각도 분포는 **Critical 25 · High 30 · Medium 13**입니다.
같은 재현율이라도 **Critical을 몇 건 잡았는지**로 한 번 더 갈라 보세요.
결제 실패로 직결되는 결함을 놓치면서 대비 문제만 잡는 서비스는 실전에서 쓸모가 없습니다.

### 난이도 4층

`DEFECTS.md`에 결함을 탐지 난이도별로 나눠뒀습니다. **어디까지 도달하는지가 곧 등급**입니다.

| 층 | 건수 | 내용 |
|---|---|---|
| 정적 분석만으로 | 22 | 대비·폰트 크기·alt·lang·랜드마크 — 못 잡으면 기본기 부족 |
| 렌더링 + 뷰포트 조작 | 10 | 가로 스크롤, 잘린 메뉴, 시각적 위계 붕괴 |
| **실제 상호작용 수행** | 16 | 담기 무반응, 조용한 실패, 폼 초기화 — **여기서 변별력이 갈림** |
| **의미·맥락 판단** | 20 | "확인" CTA, 숨은 배송비, 강제 회원가입 — **LLM 없이는 사실상 불가능** |

---

## 스모크 테스트

픽스처 자체가 설계대로 동작하는지 확인하는 자체 테스트입니다.
의존성 없이 설치된 Chrome/Edge를 CDP로 직접 구동합니다.

```bash
python -m http.server 8765      # 레포 루트에서
node ux-testbed/smoke-test.js   # 다른 터미널에서
```

40개 항목을 검사합니다.

- **CLEAN**: 담기 피드백 · 배지 갱신 · 배송비 사전 고지 · 인라인 검증 · 로딩 상태 · 주문 완료까지 전체 플로우
- **FLAWED**: 각 결함(null 옵션, 조용한 실패, 숨은 배송비, 즉시 삭제, 폼 초기화, 자동 팝업 등)이 실제로 재현되는지
- 375px 뷰포트 가로 스크롤 유무 (clean 없음 / flawed 발생)
- 접근성 정적 지표 대조 (`lang`, `alt`, `h1`, `main`, skip link, 본문 폰트 크기)

**픽스처를 수정한 뒤에는 반드시 이 테스트를 돌리세요.**
결함을 손보다 실수로 결함이 사라지면, 검증 서비스가 못 잡은 게 아니라
잡을 게 없었던 건데 점수는 떨어집니다.

---

## Playwright 연결 예시

```js
const { chromium } = require("playwright");

const BASE = "http://localhost:8000/ux-testbed";
const PAGES = ["index.html", "list.html", "product.html?id=1",
               "cart.html", "checkout.html", "complete.html"];

for (const variant of ["clean", "flawed"]) {
  const browser = await chromium.launch();
  for (const viewport of [{ width: 1440, height: 900 }, { width: 375, height: 812 }]) {
    const ctx = await browser.newContext({ viewport });
    for (const path of PAGES) {
      const page = await ctx.newPage();
      await page.goto(`${BASE}/${variant}/${path}`);
      await page.waitForLoadState("networkidle");

      // 여기서 검증 서비스에 넘길 데이터를 수집
      await page.screenshot({ path: `out/${variant}-${viewport.width}-${path.replace(/\W/g, "_")}.png`,
                              fullPage: true });
      const snapshot = await page.accessibility.snapshot();
      const html = await page.content();
      // ...
    }
    await ctx.close();
  }
  await browser.close();
}
```

> **주의:** 자동 팝업은 로드 10초 뒤에 뜹니다.
> 팝업까지 검증하려면 `waitForTimeout(11000)`을, 팝업을 피하려면 10초 안에 캡처를 끝내세요.

---

## 결함을 더 넣거나 빼려면

- `flawed/assets/style.css` — 시각적 결함(대비·크기·간격·반응형)
- `flawed/assets/app.js` — 동작 결함(피드백 없음·조용한 실패·숨은 배송비·팝업)
- 각 페이지 HTML — 구조·카피·폼 관련 결함

모든 결함에 `[D-xx]` 주석이 달려 있습니다. 주석과 해당 코드를 함께 제거하면
**난이도를 조절한 픽스처**를 만들 수 있습니다.
새 결함을 추가할 때는 `DEFECTS.md`의 집계 표도 함께 갱신하세요.

---

## 앞으로

- [ ] SPA(React/Next) 버전 추가 — 하이드레이션 환경에서도 검증되는지 확인
- [ ] 검증 결과를 `DEFECTS.md`의 `D-xx` ID와 자동 매칭하는 채점 스크립트
- [ ] 결함 수를 줄인 난이도별 픽스처 (easy / hard)

---

MOJI STORE는 테스트용 가상 쇼핑몰입니다.
상품·회사·연락처 정보는 모두 허구이며, 실제 주문·결제는 처리되지 않습니다.
