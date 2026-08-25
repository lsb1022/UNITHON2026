"""LLM 연결 점검 — 돈을 쓰기 전에 무엇이 되는지 확인한다.

    python check-llm.py                 # 현재 프로바이더 (UXAGENT_PROVIDER)
    python check-llm.py --provider qwen
    python check-llm.py --list          # 이 키로 쓸 수 있는 모델 목록만

점검 순서는 싼 것부터다. 목록 조회(무료) → 텍스트 한 마디 → 그림 한 장.
비전 호출이 제일 비싸므로 마지막이고, 앞에서 막히면 거기서 멈춘다.

모델 이름은 자주 바뀐다. config.py 에 적힌 이름이 실제로 이 키에서 보이는지
여기서 확인하고, 안 보이면 목록에서 골라 config.py 를 고칠 것.
"""
from __future__ import annotations

import argparse
import sys

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:  # noqa: BLE001
        pass

from uxagent import config
from uxagent.llm import build_client

def _png(size: int = 64) -> bytes:
    """검사용 PNG 를 즉석에서 만든다 (체크무늬).

    1x1 투명 PNG 를 쓰다가 Gemini 가 400(Unable to process input image)을 냈다.
    모델이 비전을 못 한다는 뜻이 아니라 그림이 너무 작아서였다. 실제 스크린샷
    으로는 잘 읽었다. 점검 도구가 멀쩡한 기능을 고장이라고 말하면 그 도구는
    없느니만 못하다.
    """
    import struct
    import zlib

    px = bytearray()
    for y in range(size):
        px.append(0)                                    # 행마다 필터 바이트
        for x in range(size):
            v = 0 if (x // 8 + y // 8) % 2 else 255     # 8px 체크무늬
            px += bytes((v, v, v))

    def chunk(tag: bytes, data: bytes) -> bytes:
        return (struct.pack(">I", len(data)) + tag + data
                + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF))

    return (bytes.fromhex("89504e470d0a1a0a")
            + chunk(b"IHDR", struct.pack(">IIBBBBB", size, size, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(bytes(px)))
            + chunk(b"IEND", b""))


TINY_PNG = _png()


def show_key(name: str) -> bool:
    key = config.api_key(name)
    env = config.provider(name)["key_env"]
    if not key:
        print("  [키] %s 환경변수가 없습니다." % env)
        print("       설정 후 **새 터미널**에서 다시 실행하세요:")
        print('         setx %s "발급받은키"' % env)
        return False
    print("  [키] %s 있음 (길이 %d, 끝 ...%s)" % (env, len(key), key[-4:]))
    return True


def list_models(client, limit: int = 40) -> list[str]:
    try:
        # Google 은 "models/gemini-…" 형태로 돌려준다. 접두사를 떼고 비교해야
        # config.py 의 이름과 맞는다.
        names = sorted(m.id.split("/")[-1] for m in client.models.list().data)
    except Exception as e:  # noqa: BLE001 - 목록을 막아둔 프로바이더도 있다
        print("  [목록] 조회 실패 — %s" % str(e).replace("\n", " ")[:120])
        return []
    print("  [목록] %d개" % len(names))
    for n in names[:limit]:
        print("         %s" % n)
    if len(names) > limit:
        print("         … 외 %d개" % (len(names) - limit))
    return names


def try_text(client, model: str) -> bool:
    print("\n  [텍스트] %s" % model)
    try:
        r = client.chat.completions.create(
            # 사고형 모델은 max_tokens 를 생각에 먼저 쓴다. 너무 낮게 잡으면
            # 본문이 비어서 '실패'로 오인한다.
            model=model, temperature=0, max_tokens=512,
            messages=[{"role": "user", "content": "한 단어로만 답하세요. 하늘은 무슨 색?"}])
    except Exception as e:  # noqa: BLE001
        print("           실패 — %s" % str(e).replace("\n", " ")[:200])
        return False
    u = getattr(r, "usage", None)
    body = (r.choices[0].message.content or "").strip()
    if not body:
        print("           호출은 됐는데 본문이 비었습니다 "
              "(사고형 모델이 출력 한도를 생각에 다 쓴 경우). 한도를 올려보세요.")
        return False
    print("           OK  응답 %r  (입력 %s · 출력 %s 토큰)"
          % (body[:40], getattr(u, "prompt_tokens", "?"),
             getattr(u, "completion_tokens", "?")))
    return True


def try_vision(client, model: str) -> bool:
    print("\n  [그림] %s" % model)
    from uxagent.llm import image_part
    try:
        r = client.chat.completions.create(
            model=model, temperature=0, max_tokens=512,
            messages=[{"role": "user", "content": [
                {"type": "text", "text": "이 이미지에 체크무늬가 보이면 '보임'이라고만 답하세요."},
                image_part(TINY_PNG)]}])
    except Exception as e:  # noqa: BLE001
        print("         실패 — %s" % str(e).replace("\n", " ")[:200])
        return False
    body = (r.choices[0].message.content or "").strip()
    if not body:
        print("         호출은 됐는데 본문이 비었습니다.")
        return False
    print("         OK  응답 %r" % body[:40])
    return True


def main() -> int:
    ap = argparse.ArgumentParser(description="LLM 연결 점검")
    ap.add_argument("--provider", default=None, choices=sorted(config.PROVIDERS))
    ap.add_argument("--list", action="store_true", help="모델 목록만 보고 끝낸다")
    args = ap.parse_args()

    name = args.provider or config.PROVIDER
    p = config.provider(name)
    print("=" * 62)
    print("  프로바이더: %s" % name)
    print("  주소: %s" % p["base_url"])
    print("=" * 62)

    if not show_key(name):
        return 2

    try:
        client = build_client(name)
    except Exception as e:  # noqa: BLE001
        print("  [연결] 클라이언트 생성 실패 — %s" % e)
        return 2

    names = list_models(client)
    if args.list:
        return 0

    want = {role: config.model(role, name)
            for role in ("survey", "goals", "explore", "analyze")}
    print("\n  [config.py 가 쓰려는 모델]")
    for role, m in want.items():
        mark = "" if not names else ("  ✓ 목록에 있음" if m in names else "  ⚠ 목록에 없음")
        print("         %-8s %s%s" % (role, m, mark))

    ok_text = try_text(client, want["explore"])
    ok_vis = try_vision(client, want["survey"])

    print("\n" + "-" * 62)
    if ok_text and ok_vis:
        print("  전부 통과. 이제 실제로 돌릴 수 있습니다:")
        print("    python scout.py --variant clean --shots-dir shots")
        print("    python run.py --variant buggy --only P001")
        return 0
    if ok_text and not ok_vis:
        print("  텍스트는 되고 그림이 안 됩니다. 탐색은 되지만 답사가 막힙니다.")
        print("  config.py 의 model_survey 를 목록에 있는 비전 모델로 바꾸세요.")
        return 1
    print("  텍스트가 막혔습니다. 위 오류 메시지를 그대로 보고 판단하세요.")
    print("  429 = 잔액/쿼터 문제, 401·403 = 키 문제, 404 = 모델 이름 문제.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
