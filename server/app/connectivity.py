"""프로젝트 링크 연결 검사.

브라우저에서 직접 남의 사이트를 fetch 하면 CORS에 막힌다. 그래서 서버가 대신 열어 본다.

여기서 두 가지를 따로 판정한다 — 섞으면 화면이 거짓말을 한다.
  1. 도달 가능한가        → 답사(scout)를 돌릴 수 있는가
  2. iframe 에 넣을 수 있는가 → 미리보기를 보여줄 수 있는가
사이트는 멀쩡히 열리면서 X-Frame-Options 로 임베드만 막는 경우가 매우 흔하다.
그때 "연결 실패"라고 적으면 사용자는 멀쩡한 주소를 고치려고 헤맨다.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from urllib.parse import urlparse

import httpx

TIMEOUT = httpx.Timeout(8.0, connect=4.0)
USER_AGENT = "UXLab-ConnectivityCheck/0.1 (+https://github.com/unithon2026)"

TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.IGNORECASE | re.DOTALL)
LINK_RE = re.compile(r"<a\s[^>]*href=", re.IGNORECASE)


@dataclass
class CheckResult:
    ok: bool
    url: str
    final_url: str | None = None
    status: int | None = None
    title: str | None = None
    #: 미리보기(iframe)에 넣을 수 있는지. 도달 가능 여부와 별개다.
    embeddable: bool = False
    embed_block_reason: str | None = None
    #: 답사가 훑을 만한 링크가 몇 개나 보이는지 — 연결 카드의 "화면 N개" 힌트
    link_count: int | None = None
    error_kind: str | None = None
    message: str = ""


def normalize(url: str) -> str:
    url = url.strip()
    if not url:
        return ""
    if not re.match(r"^https?://", url, re.IGNORECASE):
        url = f"https://{url}"
    return url


def _embed_verdict(headers: httpx.Headers) -> tuple[bool, str | None]:
    xfo = (headers.get("x-frame-options") or "").strip().lower()
    if xfo in {"deny", "sameorigin"} or xfo.startswith("allow-from"):
        return False, f"X-Frame-Options: {xfo}"

    csp = (headers.get("content-security-policy") or "").lower()
    match = re.search(r"frame-ancestors([^;]*)", csp)
    if match:
        allowed = match.group(1).strip()
        if allowed in {"'none'", "'self'"}:
            return False, f"CSP frame-ancestors {allowed}"

    return True, None


def check(url: str) -> CheckResult:
    target = normalize(url)
    if not target:
        return CheckResult(ok=False, url=url, error_kind="empty", message="주소를 입력해 주세요.")

    parsed = urlparse(target)
    if not parsed.netloc:
        return CheckResult(ok=False, url=target, error_kind="invalid", message="주소 형식이 올바르지 않아요.")

    try:
        with httpx.Client(
            follow_redirects=True, timeout=TIMEOUT, headers={"User-Agent": USER_AGENT}
        ) as client:
            response = client.get(target)
    except httpx.ConnectTimeout:
        return CheckResult(ok=False, url=target, error_kind="timeout", message="연결이 시간 내에 되지 않았어요.")
    except httpx.ReadTimeout:
        return CheckResult(ok=False, url=target, error_kind="timeout", message="응답이 너무 느려요.")
    except httpx.ConnectError as exc:
        # DNS 실패와 거절을 나눈다. 오타와 방화벽은 사용자가 할 일이 다르다.
        kind = "dns" if "getaddrinfo" in str(exc).lower() or "name or service" in str(exc).lower() else "refused"
        message = "주소를 찾을 수 없어요. 철자를 확인해 주세요." if kind == "dns" else "서버가 연결을 거절했어요."
        return CheckResult(ok=False, url=target, error_kind=kind, message=message)
    except httpx.TransportError as exc:
        return CheckResult(ok=False, url=target, error_kind="transport", message=f"연결하지 못했어요. ({type(exc).__name__})")

    embeddable, block_reason = _embed_verdict(response.headers)

    if response.status_code >= 400:
        return CheckResult(
            ok=False,
            url=target,
            final_url=str(response.url),
            status=response.status_code,
            embeddable=embeddable,
            embed_block_reason=block_reason,
            error_kind="http_error",
            message=f"서버가 {response.status_code} 를 돌려줬어요.",
        )

    body = response.text if "text/html" in response.headers.get("content-type", "") else ""
    title_match = TITLE_RE.search(body)

    return CheckResult(
        ok=True,
        url=target,
        final_url=str(response.url),
        status=response.status_code,
        title=title_match.group(1).strip()[:120] if title_match else None,
        embeddable=embeddable,
        embed_block_reason=block_reason,
        link_count=len(LINK_RE.findall(body)) or None,
        message="연결할 수 있어요",
    )


def check_as_dict(url: str) -> dict:
    return asdict(check(url))
