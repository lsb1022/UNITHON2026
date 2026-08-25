"""답사 대상 URL을 찾는다. 3층 구조.

  1층 링크 추적   — 어떤 사이트에도 통하지만 <a href>가 없는 페이지는 못 간다
  2층 디렉터리    — 로컬 정적 사이트일 때만. 파일시스템이 곧 사이트맵이다
  3층 --extra     — 사람이 아는 특수 URL (?id=999 같은 상태)

우리 테스트베드는 1층이 5/6(complete.html은 checkout.html의 location.href로만
진입해 inbound <a>가 없다), 2층까지 켜면 6/6이 된다.

템플릿 정규화가 핵심이다. product.html?id=1..12 를 그대로 세면 12페이지가 되어
답사 예산을 같은 템플릿 찍는 데 다 쓴다. 쿼리를 벗겨 6종으로 접는다.
"""
from __future__ import annotations

import os
from urllib.parse import urljoin, urlparse, urlsplit, parse_qsl, urlencode

from . import config

# 이 쿼리 파라미터는 페이지 '종류'가 아니라 '상태'다. 템플릿 키에서 뺀다.
STATE_PARAMS = {"id", "cat", "q", "page", "sort"}


def _fold_segment(seg: str) -> str:
    """경로 한 토막이 '식별자'면 자리표시자로 접는다.

    남의 사이트는 상품 번호를 쿼리가 아니라 경로에 둔다 —
    `/product/44`, `/product/130` 은 같은 화면이다. 접지 않으면 답사가
    같은 템플릿을 몇 번씩 세어 페이지 예산을 다 써버린다.

    숫자거나, UUID·해시처럼 긴 데다 사람 말이 아닌 토막만 접는다.
    `/computers`, `/phones` 같은 진짜 분류는 건드리지 않는다.
    """
    if not seg:
        return seg
    if seg.isdigit():
        return "{id}"
    if len(seg) >= 12 and not any(c in seg for c in "-_.") and seg.isalnum() \
            and any(c.isdigit() for c in seg):
        return "{id}"
    if len(seg) >= 20 and seg.count("-") >= 4:      # UUID 꼴
        return "{id}"
    return seg


def template_key(url: str) -> str:
    """URL을 페이지 템플릿 단위로 접는다.

    product.html?id=7  -> product.html
    list.html?cat=상의 -> list.html
    /product/44        -> /product/{id}
    쿼리에 STATE_PARAMS 밖의 키가 있으면 그건 다른 화면일 수 있으니 남긴다.
    """
    # 조각(#목차)은 같은 문서 안의 위치라 화면이 아니다. 떼지 않으면
    # '숭실대학교' 와 '숭실대학교#' 가 서로 다른 화면으로 세어진다.
    s = urlsplit(url)
    keep = [(k, v) for k, v in parse_qsl(s.query) if k not in STATE_PARAMS]
    path = s.path or "/"
    path = "/".join(_fold_segment(x) for x in path.split("/"))
    return path + (f"?{urlencode(keep)}" if keep else "")


def same_site(url: str, root: str) -> bool:
    a, b = urlparse(url), urlparse(root)
    if (a.scheme, a.netloc) != (b.scheme, b.netloc):
        return False
    base_dir = b.path.rstrip("/") + "/"
    return a.path.startswith(base_dir)


def rel_path(url: str, root: str) -> str:
    """지도에 실을 짧은 경로. root 기준 상대."""
    base_dir = urlparse(root).path.rstrip("/") + "/"
    s = urlsplit(url)
    p = s.path
    if p.startswith(base_dir):
        p = "/" + p[len(base_dir):]
    return p + (f"?{s.query}" if s.query else "")


# ── 1층: 링크 추적 ─────────────────────────────────────────────────

async def crawl_links(page, root: str, max_pages: int, max_depth: int,
                      start: str | None = None) -> tuple[list[str], dict]:
    """<a href>를 따라가며 템플릿 단위로 대표 URL을 모은다.

    반환: (대표 URL 목록, {템플릿키: [링크로 이어진 템플릿키...]})

    `start` 를 주면 거기서 출발한다. 우리 테스트베드는 첫 화면이 늘
    `/index.html` 이지만 남의 사이트는 그런 파일이 없다 — 그대로 붙이면
    404 한 장을 지도로 만들고 끝난다.
    """
    start = start or (root.rstrip("/") + "/index.html")
    seen: dict[str, str] = {}          # 템플릿키 -> 대표 URL
    edges: dict[str, list[str]] = {}
    queue = [(start, 0)]

    while queue and len(seen) < max_pages:
        url, depth = queue.pop(0)
        key = template_key(url)
        if key in seen or depth > max_depth:
            continue
        try:
            await page.goto(url, wait_until="domcontentloaded",
                            timeout=config.STEP_TIMEOUT_MS)
        except Exception:  # noqa: BLE001 - 못 가는 링크는 조용히 건너뛴다
            continue
        seen[key] = url

        hrefs = await page.eval_on_selector_all(
            "a[href]", "els => els.map(e => e.getAttribute('href'))"
        )
        out: list[str] = []
        for h in hrefs:
            if not h or h.startswith(("#", "javascript:", "mailto:", "tel:")):
                continue
            nxt = urljoin(url, h)
            if not same_site(nxt, root):
                continue
            k = template_key(nxt)
            if k not in out:
                out.append(k)
            if k not in seen:
                queue.append((nxt, depth + 1))
        edges[key] = out

    return list(seen.values()), edges


# ── 2층: 로컬 디렉터리 ─────────────────────────────────────────────

def local_dir_for(root: str, serve_root: str | None) -> str | None:
    """http://localhost:8000/ux-testbed/flawed -> <serve_root>/ux-testbed/flawed

    serve_root 아래에 실제 폴더가 있을 때만 경로를 돌려준다.
    남의 사이트를 답사할 때는 None이 되어 이 층이 자동으로 꺼진다.
    """
    if not serve_root:
        return None
    p = urlparse(root)
    if p.hostname not in ("localhost", "127.0.0.1"):
        return None
    d = os.path.join(serve_root, *[s for s in p.path.split("/") if s])
    return d if os.path.isdir(d) else None


def list_local_pages(root: str, serve_root: str | None) -> list[str]:
    d = local_dir_for(root, serve_root)
    if not d:
        return []
    names = sorted(f for f in os.listdir(d) if f.endswith(".html"))
    return [f"{root.rstrip('/')}/{n}" for n in names]


# ── 통합 ──────────────────────────────────────────────────────────

async def discover(page, root: str, *, serve_root: str | None = None,
                   extra: list[str] | None = None,
                   start: str | None = None,
                   max_pages: int = config.SURVEY_MAX_PAGES,
                   max_depth: int = config.SURVEY_MAX_DEPTH) -> dict:
    linked, edges = await crawl_links(page, root, max_pages, max_depth, start)
    by_key: dict[str, dict] = {}
    for u in linked:
        by_key[template_key(u)] = {"url": u, "found_by": "link"}

    for u in list_local_pages(root, serve_root):
        k = template_key(u)
        if k not in by_key:
            by_key[k] = {"url": u, "found_by": "dir"}   # 링크로는 못 간 페이지

    for u in extra or []:
        full = u if u.startswith("http") else f"{root.rstrip('/')}/{u.lstrip('/')}"
        k = template_key(full)
        # --extra 는 상태 지정이 목적이므로 템플릿이 겹쳐도 별도 항목으로 남긴다
        by_key.setdefault(k + "#extra", {"url": full, "found_by": "extra"})

    targets = list(by_key.values())[:max_pages]
    return {
        "targets": targets,
        "edges": edges,
        "local_dir_used": local_dir_for(root, serve_root) is not None,
        "counts": {
            "link": sum(1 for t in targets if t["found_by"] == "link"),
            "dir": sum(1 for t in targets if t["found_by"] == "dir"),
            "extra": sum(1 for t in targets if t["found_by"] == "extra"),
        },
    }
