"""사이트 첫 화면을 PNG 한 장으로 찍어 둔다.

썸네일을 iframe 으로 띄우면 진짜 웹이 카드 안에서 계속 살아 있다 —
캐러셀이 돌고 배너가 깜빡이고, 카드가 여러 장 뜨는 목록은 그만큼 시끄러워진다.
sandbox 로 스크립트를 막아도 CSS 애니메이션은 그대로 돈다.

그래서 아예 화면 한 장을 서버에서 찍는다. 브라우저(Chromium)를 헤드리스로 띄워
기획서의 답사 환경(1280×800)으로 열고, 애니메이션을 정지시킨 뒤 PNG 로 저장한다.
프론트는 그냥 <img> 다 — 움직일 여지가 없다.

찍는 데 몇 초가 걸리므로 디스크에 캐시한다. 같은 주소는 TTL 안에서 다시 찍지 않는다.
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import time
from pathlib import Path

log = logging.getLogger(__name__)

# 답사 환경과 같은 뷰포트로 찍는다. 카드에서 보는 그림과 페르소나가 보는 화면이 어긋나면
# "이 화면을 테스트했다"는 말이 거짓이 된다.
VIEWPORT_W = 1280
VIEWPORT_H = 800

CACHE_DIR = Path(__file__).resolve().parent.parent / ".thumbs"
CACHE_TTL_SECONDS = 24 * 60 * 60

# 페이지가 끝내 조용해지지 않는 사이트(폴링·광고)가 있다. 무한정 기다리지 않는다.
NAV_TIMEOUT_MS = 20_000
# 폰트와 첫 이미지가 들어올 시간. 이게 없으면 글자가 빠진 화면이 찍힌다.
SETTLE_MS = 1_500

# 애니메이션·전환·스크롤 보정을 전부 죽인 뒤 찍는다. 스크린샷은 어차피 정지 화면이지만,
# 캡처 순간 요소가 화면 밖으로 날아가 있는(등장 애니메이션 중간) 상태를 막아 준다.
FREEZE_CSS = """
*, *::before, *::after {
  animation-play-state: paused !important;
  animation-delay: 0s !important;
  animation-duration: 0s !important;
  transition: none !important;
  caret-color: transparent !important;
}
html { scroll-behavior: auto !important; }
"""

_browser = None
_playwright = None
# Chromium 하나를 재사용한다. 요청마다 띄우면 한 장에 1초 넘게 더 든다.
# 동시에 여러 장을 찍으면 개발 노트북이 버겁다 — 두 장까지만 허용한다.
_slots = asyncio.Semaphore(2)
_boot_lock = asyncio.Lock()
_available: bool | None = None


def _cache_path(url: str) -> Path:
    return CACHE_DIR / f"{hashlib.sha256(url.encode()).hexdigest()}.png"


def cached(url: str) -> bytes | None:
    """아직 살아 있는 캐시가 있으면 돌려준다."""
    path = _cache_path(url)
    try:
        stat = path.stat()
    except OSError:
        return None
    if time.time() - stat.st_mtime > CACHE_TTL_SECONDS:
        return None
    try:
        return path.read_bytes()
    except OSError:
        return None


async def _get_browser():
    """Chromium 을 한 번만 띄우고 재사용한다."""
    global _browser, _playwright, _available

    if _browser is not None:
        return _browser

    async with _boot_lock:
        if _browser is not None:
            return _browser
        if _available is False:
            return None
        try:
            from playwright.async_api import async_playwright
        except ImportError:
            # playwright 가 없는 환경에서도 서버는 떠야 한다. 썸네일만 포기한다.
            log.warning("playwright 가 없어 썸네일을 찍지 않습니다 (기본 이미지로 대체)")
            _available = False
            return None
        try:
            _playwright = await async_playwright().start()
            _browser = await _playwright.chromium.launch(
                args=["--disable-dev-shm-usage", "--hide-scrollbars"]
            )
            _available = True
        except Exception as error:  # 브라우저 바이너리가 안 깔린 경우 등
            log.warning("Chromium 을 띄우지 못했습니다: %s", error)
            _available = False
            return None
    return _browser


async def capture(url: str) -> bytes | None:
    """주소 하나를 PNG 로 찍는다. 캐시가 있으면 그걸 쓴다. 실패하면 None."""
    hit = cached(url)
    if hit is not None:
        return hit

    browser = await _get_browser()
    if browser is None:
        return None

    async with _slots:
        # 기다리는 동안 다른 요청이 이미 찍어 놨을 수 있다.
        hit = cached(url)
        if hit is not None:
            return hit

        context = None
        try:
            context = await browser.new_context(
                viewport={"width": VIEWPORT_W, "height": VIEWPORT_H},
                # 모바일 전용 화면으로 튕기지 않도록 평범한 데스크톱으로 신분을 밝힌다.
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
                ),
                locale="ko-KR",
                # 사이트가 자동재생·모션을 스스로 줄여 주는 경우가 많다.
                reduced_motion="reduce",
                ignore_https_errors=True,
            )
            page = await context.new_page()
            await page.goto(url, wait_until="domcontentloaded", timeout=NAV_TIMEOUT_MS)
            try:
                await page.wait_for_load_state("networkidle", timeout=SETTLE_MS * 2)
            except Exception:
                # 계속 통신하는 사이트도 있다. 여기서 실패해도 화면은 이미 그려져 있다.
                pass
            await page.add_style_tag(content=FREEZE_CSS)
            await page.wait_for_timeout(SETTLE_MS)
            png = await page.screenshot(type="png", animations="disabled")
        except Exception as error:
            log.info("썸네일 실패 %s: %s", url, error)
            return None
        finally:
            if context is not None:
                try:
                    await context.close()
                except Exception:
                    pass

    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        # 반쯤 쓰다 만 파일을 다음 요청이 읽지 않도록 옮겨 담는다.
        temporary = _cache_path(url).with_suffix(".part")
        temporary.write_bytes(png)
        temporary.replace(_cache_path(url))
    except OSError as error:
        log.info("썸네일 캐시 저장 실패 %s: %s", url, error)

    return png


async def shutdown() -> None:
    """서버가 내려갈 때 Chromium 도 같이 내린다."""
    global _browser, _playwright
    if _browser is not None:
        try:
            await _browser.close()
        except Exception:
            pass
        _browser = None
    if _playwright is not None:
        try:
            await _playwright.stop()
        except Exception:
            pass
        _playwright = None
