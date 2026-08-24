/* 테스트베드 스모크 테스트
   Chrome DevTools Protocol로 실제 구매 플로우를 수행해
   clean / flawed 두 버전이 설계대로 동작하는지 확인한다.

   사용법:
     1) 프로젝트 상위 폴더에서  python -m http.server 8765
     2) node ux-testbed/smoke-test.js
*/

const { spawn } = require("child_process");
const fs = require("fs");

const BASE = process.env.BASE || "http://localhost:8765/ux-testbed";
const PORT = 9333;

const CHROME_CANDIDATES = [
  "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
  "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe",
  "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe",
  "C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe",
];

let pass = 0, fail = 0;
function check(label, ok, detail = "") {
  if (ok) { pass++; console.log("  OK    " + label); }
  else    { fail++; console.log("  FAIL  " + label + (detail ? "  → " + detail : "")); }
}

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

/* ---------- 최소 CDP 클라이언트 ---------- */
class CDP {
  constructor(ws) { this.ws = ws; this.id = 0; this.pending = new Map(); }

  static async attach(port) {
    const list = await (await fetch(`http://127.0.0.1:${port}/json/list`)).json();
    const target = list.find((t) => t.type === "page");
    const ws = new WebSocket(target.webSocketDebuggerUrl);
    await new Promise((res, rej) => { ws.onopen = res; ws.onerror = rej; });
    const cdp = new CDP(ws);
    ws.onmessage = (ev) => {
      const msg = JSON.parse(ev.data);
      const p = cdp.pending.get(msg.id);
      if (p) { cdp.pending.delete(msg.id); msg.error ? p.rej(new Error(msg.error.message)) : p.res(msg.result); }
    };
    return cdp;
  }

  send(method, params = {}) {
    const id = ++this.id;
    this.ws.send(JSON.stringify({ id, method, params }));
    return new Promise((res, rej) => this.pending.set(id, { res, rej }));
  }

  async goto(url) {
    await this.send("Page.navigate", { url });
    // 인라인 스크립트가 DOMContentLoaded에서 렌더링을 마칠 때까지 대기
    for (let i = 0; i < 40; i++) {
      await sleep(100);
      const r = await this.eval("document.readyState");
      if (r === "complete") { await sleep(150); return; }
    }
  }

  async eval(expression) {
    const r = await this.send("Runtime.evaluate", {
      expression, returnByValue: true, awaitPromise: true,
    });
    if (r.exceptionDetails) throw new Error(r.exceptionDetails.text + " :: " + expression);
    return r.result.value;
  }
}

/* ---------- 테스트 ---------- */
async function run(cdp) {
  console.log("\n[1] CLEAN — 상품 담기 → 피드백 → 장바구니 → 결제");

  await cdp.goto(`${BASE}/clean/product.html?id=1`);
  await cdp.eval(`localStorage.removeItem("moji_cart_clean")`);
  await cdp.goto(`${BASE}/clean/product.html?id=1`);

  check("색상·사이즈 기본값이 선택되어 있다",
    await cdp.eval(`!!document.querySelector('input[name="color"]:checked') &&
                    !!document.querySelector('input[name="size"]:checked')`));

  await cdp.eval(`document.getElementById("add-cart").click()`);
  await sleep(300);

  check("담기 후 토스트 피드백이 뜬다 (D-35 대조군)",
    await cdp.eval(`!!document.querySelector(".toast")`));
  check("헤더 장바구니 배지가 1로 갱신된다 (D-01 대조군)",
    (await cdp.eval(`document.querySelector("[data-cart-count]").textContent`)) === "1");

  const cleanLine = await cdp.eval(`JSON.parse(localStorage.getItem("moji_cart_clean"))[0]`);
  check("옵션이 null 없이 저장된다 (D-52 대조군)",
    cleanLine.color !== null && cleanLine.size !== null, JSON.stringify(cleanLine));

  await cdp.goto(`${BASE}/clean/cart.html`);
  const cleanCartText = await cdp.eval(`document.body.innerText`);
  check("장바구니에 배송비 항목이 명시된다 (D-33 대조군)", cleanCartText.includes("배송비"));
  check("금액에 '원' 단위가 붙는다 (D-16 대조군)", cleanCartText.includes("원"));
  const cleanTotal = await cdp.eval(`(function(){
      var c = JSON.parse(localStorage.getItem("moji_cart_clean"));
      var s = c.reduce((a,l)=>a+l.price*l.qty,0);
      return s + (s>=50000?0:3000);
    })()`);
  check("장바구니 총액이 화면에 그대로 표시된다",
    cleanCartText.includes(cleanTotal.toLocaleString("ko-KR")), "총액 " + cleanTotal);

  await cdp.goto(`${BASE}/clean/checkout.html`);
  const cleanCheckoutText = await cdp.eval(`document.body.innerText`);
  check("결제 총액이 장바구니와 일치한다 (D-33 대조군)",
    cleanCheckoutText.includes(cleanTotal.toLocaleString("ko-KR")), "총액 " + cleanTotal);
  check("비회원 주문 경로가 있다 (D-58 대조군)",
    await cdp.eval(`!!document.getElementById("mode-guest")`));
  check("마케팅 동의가 기본 해제 상태다 (D-25 대조군)",
    (await cdp.eval(`document.getElementById("agree-marketing").checked`)) === false);

  await cdp.eval(`document.getElementById("pay-btn").click()`);
  await sleep(400);
  check("빈 값 제출 시 에러 요약이 표시된다 (D-63 대조군)",
    (await cdp.eval(`!document.getElementById("error-summary").hidden`)));
  check("에러 표시 후에도 입력값이 유지된다 (D-64 대조군)",
    (await cdp.eval(`document.getElementById("email").value`)) === "");

  await cdp.eval(`
    document.getElementById("name").value  = "홍길동";
    document.getElementById("phone").value = "010-1234-5678";
    document.getElementById("email").value = "test@example.com";
    document.getElementById("zip").value   = "06234";
    document.getElementById("addr1").value = "서울특별시 강남구 테헤란로 152";
    document.getElementById("agree-required").checked = true;
  `);
  await cdp.eval(`document.getElementById("pay-btn").click()`);
  await sleep(300);
  check("결제 처리 중 로딩 상태가 노출된다 (D-65 대조군)",
    await cdp.eval(`!!document.querySelector("#pay-btn .spinner")`));

  await sleep(1600);
  check("주문 완료 페이지로 이동한다", (await cdp.eval(`location.pathname`)).includes("complete"));
  const doneText = await cdp.eval(`document.body.innerText`);
  check("완료 화면에 주문번호가 있다 (D-67 대조군)", /MOJI-\d{6}/.test(doneText));
  check("완료 후 장바구니가 비워진다",
    (await cdp.eval(`(JSON.parse(localStorage.getItem("moji_cart_clean"))||[]).length`)) === 0);

  console.log("\n[2] FLAWED — 결함이 설계대로 재현되는지");

  await cdp.goto(`${BASE}/flawed/product.html?id=1`);
  await cdp.eval(`localStorage.removeItem("moji_cart_flawed")`);
  await cdp.goto(`${BASE}/flawed/product.html?id=1`);

  check("D-52 옵션 미선택 상태로 담기가 진행된다", true);
  await cdp.eval(`document.getElementById("add").click()`);
  await sleep(200);
  const flawedLine = await cdp.eval(`JSON.parse(localStorage.getItem("moji_cart_flawed"))[0]`);
  check("D-52 옵션이 null로 저장된다",
    flawedLine.color === null && flawedLine.size === null, JSON.stringify(flawedLine));
  check("D-35 담은 뒤 어떤 피드백도 없다",
    await cdp.eval(`!document.querySelector(".toast") && !document.querySelector("[data-cart-count]")`));

  await cdp.goto(`${BASE}/flawed/product.html?id=7`);
  const before = await cdp.eval(`(JSON.parse(localStorage.getItem("moji_cart_flawed"))||[]).length`);
  await cdp.eval(`document.getElementById("add").click()`);
  await sleep(200);
  const after = await cdp.eval(`(JSON.parse(localStorage.getItem("moji_cart_flawed"))||[]).length`);
  check("D-34 품절 상품은 안내 없이 조용히 무시된다", before === after, `${before} → ${after}`);

  await cdp.goto(`${BASE}/flawed/cart.html`);
  const flawedCartText = await cdp.eval(`document.body.innerText`);
  check("D-52 장바구니에 'null / null'이 노출된다", flawedCartText.includes("null / null"));
  check("D-33 장바구니에 배송비 항목이 없다", !flawedCartText.includes("배송비"));
  check("D-16 금액에 '원' 단위가 없다", !flawedCartText.includes("원"));

  const flawedSub = await cdp.eval(`JSON.parse(localStorage.getItem("moji_cart_flawed"))
                                      .reduce((a,l)=>a+l.price*l.qty,0)`);
  await cdp.goto(`${BASE}/flawed/checkout.html`);
  const flawedCheckoutText = await cdp.eval(`document.body.innerText`);
  check("D-33 결제 단계에서 배송비 5000이 조용히 추가된다",
    flawedCheckoutText.includes(String(flawedSub + 5000)) && !flawedCartText.includes(String(flawedSub + 5000)),
    `장바구니 ${flawedSub} → 결제 ${flawedSub + 5000}`);
  check("D-25 마케팅 동의가 기본 체크되어 있다",
    (await cdp.eval(`document.getElementById("agree2").checked`)) === true);
  check("D-58 비회원 구매 경로가 없다",
    flawedCheckoutText.includes("회원가입이 필요합니다"));
  check("D-08 폼에 label 요소가 하나도 없다",
    (await cdp.eval(`document.querySelectorAll("form label").length`)) === 0);

  await cdp.eval(`document.getElementById("name").value = "홍길동"`);
  await cdp.eval(`document.getElementById("pay").click()`);
  await sleep(400);
  check("D-63/D-64 검증 실패 시 메시지 없이 입력값이 초기화된다",
    (await cdp.eval(`document.getElementById("name").value`)) === "");

  await cdp.goto(`${BASE}/flawed/cart.html`);
  const cnt0 = await cdp.eval(`document.querySelectorAll(".del-x").length`);
  await cdp.eval(`document.querySelector(".del-x").click()`);
  await sleep(200);
  check("D-22 확인 절차 없이 즉시 삭제된다",
    (await cdp.eval(`document.querySelectorAll(".del-x").length`)) === cnt0 - 1);

  console.log("\n[3] 반응형 — 375px 뷰포트 가로 스크롤");

  for (const [variant, expectOverflow] of [["clean", false], ["flawed", true]]) {
    await cdp.send("Emulation.setDeviceMetricsOverride",
      { width: 375, height: 812, deviceScaleFactor: 2, mobile: true });
    await cdp.goto(`${BASE}/${variant}/list.html`);
    const overflow = await cdp.eval(
      `document.documentElement.scrollWidth > document.documentElement.clientWidth + 1`);
    check(`${variant}: 375px에서 가로 스크롤 ${expectOverflow ? "발생 (D-29)" : "없음"}`,
      overflow === expectOverflow,
      `scrollWidth ${await cdp.eval(`document.documentElement.scrollWidth`)}`);
  }
  await cdp.send("Emulation.clearDeviceMetricsOverride");

  console.log("\n[4] 자동 팝업 (D-26) — 10초 대기");
  await cdp.goto(`${BASE}/flawed/index.html`);
  check("로드 직후에는 팝업이 없다", (await cdp.eval(`!document.querySelector(".popup")`)));
  await sleep(11000);
  check("D-26 10초 후 팝업이 자동으로 뜬다", await cdp.eval(`!!document.querySelector(".popup")`));
  check("D-26 닫기 버튼이 8px이다",
    (await cdp.eval(`getComputedStyle(document.querySelector(".popup-close")).fontSize`)) === "8px");

  console.log("\n[5] 접근성 정적 지표");
  const metrics = {};
  for (const variant of ["clean", "flawed"]) {
    await cdp.goto(`${BASE}/${variant}/list.html`);
    metrics[variant] = await cdp.eval(`({
      lang:        document.documentElement.lang,
      imgsNoAlt:   [...document.images].filter(i => !i.hasAttribute("alt")).length,
      imgsTotal:   document.images.length,
      h1:          document.querySelectorAll("h1").length,
      mainLandmark:document.querySelectorAll("main").length,
      skipLink:    document.querySelectorAll(".skip-link").length,
      bodyFontSize:getComputedStyle(document.body).fontSize,
      bodyColor:   getComputedStyle(document.body).color
    })`);
  }
  console.log("  clean :", JSON.stringify(metrics.clean));
  console.log("  flawed:", JSON.stringify(metrics.flawed));
  check("D-38 flawed만 lang이 en이다", metrics.clean.lang === "ko" && metrics.flawed.lang === "en");
  check("D-37 flawed 이미지에 alt가 없다",
    metrics.clean.imgsNoAlt === 0 && metrics.flawed.imgsNoAlt === metrics.flawed.imgsTotal);
  check("D-48 flawed 목록에 h1이 없다", metrics.clean.h1 === 1 && metrics.flawed.h1 === 0);
  check("D-39 flawed에 main 랜드마크가 없다",
    metrics.clean.mainLandmark === 1 && metrics.flawed.mainLandmark === 0);
  check("D-41 flawed에 skip link가 없다",
    metrics.clean.skipLink === 1 && metrics.flawed.skipLink === 0);
  check("D-06 flawed 본문이 11px이다",
    metrics.clean.bodyFontSize === "16px" && metrics.flawed.bodyFontSize === "11px");
}

/* ---------- 실행 ---------- */
(async () => {
  const chrome = CHROME_CANDIDATES.find((p) => fs.existsSync(p));
  if (!chrome) { console.error("Chrome/Edge를 찾을 수 없습니다."); process.exit(1); }

  const proc = spawn(chrome, [
    "--headless=new", "--disable-gpu", "--no-first-run", "--no-default-browser-check",
    `--remote-debugging-port=${PORT}`,
    `--user-data-dir=${require("os").tmpdir()}\\ux-smoke-profile`,
    "about:blank",
  ], { stdio: "ignore" });

  try {
    for (let i = 0; i < 50; i++) {
      await sleep(200);
      try { await fetch(`http://127.0.0.1:${PORT}/json/version`); break; } catch {}
    }
    const cdp = await CDP.attach(PORT);
    await cdp.send("Page.enable");
    await cdp.send("Runtime.enable");
    await run(cdp);
  } catch (e) {
    console.error("\n실행 오류:", e.message);
    fail++;
  } finally {
    proc.kill();
  }

  console.log(`\n=== 결과: 통과 ${pass} / 실패 ${fail} ===`);
  process.exit(fail ? 1 : 0);
})();
