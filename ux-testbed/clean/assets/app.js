/* ============================================================
   MOJI STORE — CLEAN 버전 공통 스크립트
   장바구니 상태(localStorage), 헤더 배지, 토스트, 그리드 렌더링.
   ============================================================ */

const STORE_KEY = "moji_cart_clean";
const FREE_SHIP_OVER = 50000;   // 5만원 이상 무료배송
const SHIP_FEE = 3000;          // 그 미만 3,000원 — 모든 화면에서 미리 고지한다

const $  = (sel, root = document) => root.querySelector(sel);
const $$ = (sel, root = document) => [...root.querySelectorAll(sel)];

const won = (n) => n.toLocaleString("ko-KR") + "원";
const productById = (id) => window.PRODUCTS.find((p) => p.id === Number(id));

/* ---------- 장바구니 상태 ---------- */
function getCart() {
  try { return JSON.parse(localStorage.getItem(STORE_KEY)) || []; }
  catch { return []; }
}
function saveCart(cart) {
  localStorage.setItem(STORE_KEY, JSON.stringify(cart));
  renderCartBadge();
}
function cartCount() {
  return getCart().reduce((sum, line) => sum + line.qty, 0);
}
function cartSubtotal() {
  return getCart().reduce((sum, line) => sum + line.price * line.qty, 0);
}
function shippingFee(subtotal = cartSubtotal()) {
  if (subtotal === 0) return 0;
  return subtotal >= FREE_SHIP_OVER ? 0 : SHIP_FEE;
}

function addToCart({ id, color, size, qty = 1 }) {
  const product = productById(id);
  if (!product) return { ok: false, reason: "상품을 찾을 수 없습니다." };
  if (product.soldOut) return { ok: false, reason: "품절된 상품입니다." };

  const cart = getCart();
  const key = `${id}|${color}|${size}`;
  const line = cart.find((l) => l.key === key);
  if (line) line.qty += qty;
  else cart.push({ key, id, name: product.name, price: product.price, color, size, qty });

  saveCart(cart);
  return { ok: true };
}

function updateQty(key, qty) {
  const cart = getCart();
  const line = cart.find((l) => l.key === key);
  if (!line) return;
  line.qty = Math.max(1, Math.min(99, qty));
  saveCart(cart);
}

function removeLine(key) {
  saveCart(getCart().filter((l) => l.key !== key));
}

/* ---------- 헤더 ---------- */
function renderCartBadge() {
  const count = cartCount();
  $$("[data-cart-count]").forEach((el) => {
    el.textContent = count;
    el.hidden = count === 0;
  });
  $$("[data-cart-label]").forEach((el) => {
    el.textContent = count === 0 ? "장바구니 (비어 있음)" : `장바구니, 상품 ${count}개`;
  });
}

function initHeader() {
  renderCartBadge();

  const toggle = $(".menu-toggle");
  const nav = $("#main-nav");
  if (toggle && nav) {
    toggle.addEventListener("click", () => {
      const open = nav.classList.toggle("is-open");
      toggle.setAttribute("aria-expanded", String(open));
      toggle.setAttribute("aria-label", open ? "메뉴 닫기" : "메뉴 열기");
    });
  }
}

/* ---------- 토스트 (동작 결과 피드백) ---------- */
function toast(message, link) {
  let area = $(".toast-area");
  if (!area) {
    area = document.createElement("div");
    area.className = "toast-area";
    area.setAttribute("role", "status");
    area.setAttribute("aria-live", "polite");
    document.body.appendChild(area);
  }
  const el = document.createElement("div");
  el.className = "toast";
  el.innerHTML = `<span>${message}</span>`;
  if (link) {
    const a = document.createElement("a");
    a.href = link.href;
    a.textContent = link.text;
    el.appendChild(a);
  }
  area.appendChild(el);
  setTimeout(() => el.remove(), 4500);
}

/* ---------- 상품 카드 ---------- */
function discountPct(p) {
  if (p.listPrice <= p.price) return 0;
  return Math.round((1 - p.price / p.listPrice) * 100);
}

function cardHTML(p) {
  const off = discountPct(p);
  const badgeClass = p.badge === "SALE" ? "badge badge--sale"
                   : p.badge === "NEW"  ? "badge badge--new"
                   : "badge";
  return `
  <li class="card">
    <a class="card__link" href="product.html?id=${p.id}">
      <div class="card__thumb">
        <img src="../shared/img/p${p.id}.svg"
             alt="${p.name} 상품 사진" width="600" height="750" loading="lazy">
        ${p.badge ? `<span class="${badgeClass}">${p.badge}</span>` : ""}
        ${p.soldOut ? `<span class="soldout-veil">품절</span>` : ""}
      </div>
      <h3 class="card__name">${p.name}</h3>
      <div class="card__meta">
        <span class="card__price">${won(p.price)}</span>
        ${off ? `<span class="card__list-price">${won(p.listPrice)}</span>
                 <span class="card__off">${off}% 할인</span>` : ""}
      </div>
      <p class="card__rating">별점 ${p.rating} / 5 · 리뷰 ${p.reviews}개</p>
    </a>
  </li>`;
}

function renderGrid(target, products) {
  target.innerHTML = products.map(cardHTML).join("");
}

document.addEventListener("DOMContentLoaded", initHeader);
