"""프로바이더 무관 LLM 호출부.

gemini / qwen 둘 다 OpenAI 호환이라 클라이언트는 하나로 끝난다.
바뀌는 건 base_url, 키 환경변수, 모델명뿐이고 전부 config.py에 있다.

JSON 파싱 실패를 '정상 경로'로 취급한다. response_format이 프로바이더마다
얼마나 확실히 먹는지 보장할 수 없기 때문에, 코드펜스 제거 -> 균형 잡힌
중괄호 추출 -> 재시도 순으로 내려간다.
"""
from __future__ import annotations

import base64
import json
import re
import time

from . import config


class LLMError(RuntimeError):
    pass


class Usage:
    """토큰·비용 누적기. survey_meta에 그대로 실린다."""

    def __init__(self):
        self.calls = 0
        self.tok_in = 0
        self.tok_out = 0

    def add(self, resp) -> None:
        self.calls += 1
        u = getattr(resp, "usage", None)
        if u is None:
            return
        self.tok_in += getattr(u, "prompt_tokens", 0) or 0
        self.tok_out += getattr(u, "completion_tokens", 0) or 0

    def as_dict(self, provider_name: str | None = None) -> dict:
        return {
            "calls": self.calls,
            "tokens_in": self.tok_in,
            "tokens_out": self.tok_out,
            "cost_usd": config.estimate_cost(self.tok_in, self.tok_out, provider_name),
        }


# ── JSON 추출 ─────────────────────────────────────────────────────

_FENCE = re.compile(r"^\s*```(?:json)?\s*|\s*```\s*$", re.I)


def extract_json(text: str) -> dict:
    """모델이 뱉은 문자열에서 JSON 객체를 건져낸다.

    1) 그대로 파싱  2) 코드펜스 제거  3) 첫 균형 중괄호 블록 추출
    셋 다 실패하면 LLMError. 호출부가 재시도한다.
    """
    for candidate in (text, _FENCE.sub("", text or "")):
        try:
            obj = json.loads(candidate)
            if isinstance(obj, dict):
                return obj
        except (json.JSONDecodeError, TypeError):
            pass

    start = (text or "").find("{")
    if start != -1:
        depth = 0
        in_str = False
        esc = False
        for i in range(start, len(text)):
            ch = text[i]
            if in_str:
                if esc:
                    esc = False
                elif ch == "\\":
                    esc = True
                elif ch == '"':
                    in_str = False
                continue
            if ch == '"':
                in_str = True
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    try:
                        obj = json.loads(text[start:i + 1])
                        if isinstance(obj, dict):
                            return obj
                    except json.JSONDecodeError:
                        break
    raise LLMError(f"JSON을 찾지 못함: {(text or '')[:200]}")


def _backoff(attempt: int) -> float:
    """시도 횟수에 따른 대기. 503(과부하)은 몇 초 뒤 풀리는 일이 많다."""
    tbl = config.RETRY_BACKOFF
    return tbl[min(attempt - 1, len(tbl) - 1)]


def chat_json_any(client, *, models: list[str], **kw) -> dict:
    """모델 목록을 앞에서부터 시도한다. 하나가 과부하면 다음으로 넘어간다.

    답사는 40스텝을 이어 달려야 하는데, 중간 한 번의 503 으로 전부 잃으면
    같은 돈을 두 번 쓰게 된다. 등급이 같은 모델로 갈아타는 편이 낫다.
    """
    last = None
    for i, m in enumerate(models):
        try:
            return chat_json(client, model=m, **kw)
        except LLMError as e:
            last = e
            if i + 1 < len(models):
                print("      %s 실패 → %s 로 대체" % (m, models[i + 1]), flush=True)
    raise last if last else LLMError("모델 목록이 비었습니다")


# ── 클라이언트 ────────────────────────────────────────────────────

def build_client(provider_name: str | None = None):
    from openai import OpenAI  # 지연 임포트: --mock 만 쓸 때는 필요 없다

    p = config.provider(provider_name)
    key = config.api_key(provider_name)
    if not key:
        raise LLMError(
            f"{p['key_env']} 환경변수가 없습니다. "
            f"키 없이 돌리려면 --mock 을 붙이세요."
        )
    return OpenAI(base_url=p["base_url"], api_key=key, timeout=config.REQUEST_TIMEOUT)


def image_part(png_bytes: bytes) -> dict:
    b64 = base64.b64encode(png_bytes).decode("ascii")
    return {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}}


def chat_json(
    client,
    *,
    model: str,
    system: str,
    user: str,
    images: list[bytes] | None = None,
    temperature: float = 0.0,
    usage: Usage | None = None,
    retries: int = config.MAX_RETRIES,
) -> dict:
    """JSON 객체 하나를 받아낸다. 파싱 실패도 재시도 대상."""
    content: list | str
    if images:
        content = [{"type": "text", "text": user}] + [image_part(b) for b in images]
    else:
        content = user

    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": content},
    ]

    last = None
    for attempt in range(1, retries + 1):
        try:
            resp = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                response_format={"type": "json_object"},
            )
        except Exception as e:  # noqa: BLE001 - 429/타임아웃/미지원 파라미터 전부 재시도
            # response_format 미지원이면 빼고 한 번 더 시도한다.
            if "response_format" in str(e):
                try:
                    resp = client.chat.completions.create(
                        model=model, messages=messages, temperature=temperature
                    )
                except Exception as e2:  # noqa: BLE001
                    last = e2
                    time.sleep(_backoff(attempt))
                    continue
            else:
                last = e
                time.sleep(_backoff(attempt))
                continue

        if usage is not None:
            usage.add(resp)
        try:
            return extract_json(resp.choices[0].message.content)
        except LLMError as e:
            last = e
            # 파싱 실패는 형식을 다시 못박아 재시도
            messages = messages[:2] + [
                {"role": "assistant", "content": (resp.choices[0].message.content or "")[:500]},
                {"role": "user", "content": "위 응답이 JSON으로 파싱되지 않았습니다. "
                                            "설명 없이 JSON 객체 하나만 다시 출력하세요."},
            ]

    raise LLMError(f"{retries}회 시도 실패: {last}")
