/* ============================================================
   MOJI STORE — FLAWED 버전 공통 스크립트
   ⚠ 의도적 UX 결함 포함. [D-xx] 주석이 DEFECTS.md 정답지와 대응합니다.
   ============================================================ */

const STORE_KEY = "moji_cart_flawed";

/* [D-33] 배송비 5,000원이 상품/장바구니 화면 어디에도 고지되지 않고
   결제 마지막 단계에서만 총액에 더해진다 (숨은 비용 / drip pricing) */
const HIDDEN_SHIP_FEE = 5000;

const $  = (sel, root = document) => root.querySelector(sel);
const $$ = (sel, root = document) => [...root.querySelectorAll(sel)];

/* [D-16] 통화 단위 없이 숫자만 반환 — 화면 어디에도 "원"이 붙지 않는다 */
const num = (n) => String(n);
const productById = (id) => window.PRODUCTS.find((p) => p.id === Number(id));

function getCart() {
  try { return JSON.parse(localStorage.getItem(STORE_KEY)) || []; }
  catch { return []; }
}
function saveCart(cart) {
  localStorage.setItem(STORE_KEY, JSON.stringify(cart));
  /* [D-01] 장바구니 수량 배지를 갱신하지 않는다.
     헤더에는 배지 자체가 없어서 담았는지 여부를 헤더에서 확인할 수 없다. */
}
function cartCount() {
  return getCart().reduce((s, l) => s + l.qty, 0);
}
function cartSubtotal() {
  return getCart().reduce((s, l) => s + l.price * l.qty, 0);
}

/* [D-34] 품절 상품을 담으면 아무 일도 일어나지 않는다.
   에러 메시지도, 실패 표시도 없이 조용히 무시된다 (silent failure) */
function addToCart({ id, color, size, qty = 1 }) {
  const product = productById(id);
  if (!product) return;
  if (product.soldOut) return;   // 조용히 종료

  const cart = getCart();
  const key = `${id}|${color}|${size}`;
  const line = cart.find((l) => l.key === key);
  if (line) line.qty += qty;
  else cart.push({ key, id, name: product.name, price: product.price, color, size, qty });
  saveCart(cart);
  /* [D-35] 담은 뒤 토스트·모달·배지 등 어떤 성공 피드백도 주지 않는다 */
}

function updateQty(key, qty) {
  const cart = getCart();
  const line = cart.find((l) => l.key === key);
  if (!line) return;
  /* [D-36] 수량 하한 검증이 없어 0이나 음수가 되고, 총액이 음수로 표시될 수 있다 */
  line.qty = qty;
  saveCart(cart);
}

/* [D-22] 확인 절차도, 실행취소도 없이 즉시 삭제한다 */
function removeLine(key) {
  saveCart(getCart().filter((l) => l.key !== key));
}

function cardHTML(p) {
  return `
  <li class="card">
    <a href="product.html?id=${p.id}">
      <!-- [D-37] 모든 상품 이미지에 alt 속성이 없다 -->
      <img src="../shared/img/p${p.id}.svg">
      <div class="card-name">${p.name}</div>
      <div>
        <span class="card-price">${num(p.price)}</span>
        ${p.listPrice > p.price ? `<span class="card-list-price">${num(p.listPrice)}</span>` : ""}
      </div>
      ${p.soldOut ? `<div class="soldout">sold out</div>` : ""}
      ${p.badge ? `<div class="badge">${p.badge}</div>` : ""}
    </a>
    <!-- [D-10] div 가짜 버튼: role도 tabindex도 없어 키보드로 도달할 수 없다
         [D-13] 문구가 "확인"이라 무엇이 일어나는지 알 수 없다 -->
    <div class="fake-btn" data-add="${p.id}">확인</div>
  </li>`;
}

function renderGrid(target, products) {
  target.innerHTML = products.map(cardHTML).join("");
  target.addEventListener("click", (e) => {
    const el = e.target.closest("[data-add]");
    if (!el) return;
    const p = productById(el.dataset.add);
    addToCart({ id: p.id, color: p.colors[0], size: p.sizes[0], qty: 1 });
    /* 피드백 없음 — 사용자는 담겼는지 알 수 없다 */
  });
}

/* [D-26] 10초 후 자동으로 뜨는 프로모션 팝업.
   ESC로 닫히지 않고, 배경 클릭으로도 닫히지 않으며, 닫기 버튼은 8px이다. */
function schedulePopup() {
  setTimeout(() => {
    if (document.querySelector(".popup")) return;
    const back = document.createElement("div");
    back.className = "popup-backdrop";
    const box = document.createElement("div");
    box.className = "popup";
    box.innerHTML = `
      <span class="popup-close" title="닫기">x</span>
      <h2>지금 가입하면 할인!</h2>
      <p>첫 구매 고객 대상 쿠폰을 드립니다. 아래에서 이메일을 입력하세요.</p>
      <input class="inp" placeholder="이메일" style="width:70%">
      <div class="fake-btn" style="margin-left:4px">확인</div>`;
    document.body.appendChild(back);
    document.body.appendChild(box);
    box.querySelector(".popup-close").addEventListener("click", () => {
      box.remove(); back.remove();
    });
  }, 10000);
}

document.addEventListener("DOMContentLoaded", schedulePopup);
