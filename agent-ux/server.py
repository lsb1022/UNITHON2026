"""프론트가 부르는 API 서버 — 버튼 하나에 엔드포인트 하나.

    python server.py                 # 진짜 실행 (LLM 호출, 돈 듦)
    python server.py --mock          # LLM 없이. 프론트 개발용. 공짜
    python server.py --port 8080

표준 라이브러리만 쓴다. FastAPI 도 uvicorn 도 설치하지 않는다.
해커톤에서 의존성 문제로 시간을 날리는 것이 가장 아깝다.

**하는 일은 CLI 를 대신 실행해 주는 것뿐이다.** scout.py / generate.py / run.py 를
그대로 부르고, 그 출력을 로그로 흘려보내고, 다 끝나면 logs/ 의 결과를 읽어 준다.
파이프라인 로직을 여기에 다시 쓰지 않는다 — 두 벌이 되면 반드시 어긋난다.

한 번에 한 작업만 돌린다. 브라우저를 여러 개 띄우면 노트북이 못 버티고,
시연 중에 무엇이 도는지 모르게 되는 편이 더 위험하다.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import threading
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:  # noqa: BLE001
        pass

HERE = os.path.dirname(os.path.abspath(__file__))
PY = sys.executable

# 우리 쇼핑몰만 검사한다. 데모라 대상이 정해져 있고, 남의 사이트에 에이전트를
# 붙이는 것은 허락과 안전장치가 필요한 별개의 문제다.
# 여기에 없는 주소는 거부한다 — 프론트가 실수로 보내도 서버가 막는다.
ALLOWED_HOSTS = {"localhost", "127.0.0.1", "lsb1022.github.io"}

JOBS: dict[str, dict] = {}
LOCK = threading.Lock()


def _allowed(url: str) -> bool:
    try:
        host = urlparse(url).hostname or ""
    except Exception:  # noqa: BLE001
        return False
    return host in ALLOWED_HOSTS


class Job:
    """단계 여러 개를 순서대로 돌리고, 출력을 한 줄씩 모은다."""

    def __init__(self, jid: str, steps: list[dict]):
        self.id = jid
        self.steps = steps          # [{"name":..., "cmd":[...]}]
        self.stage = ""
        self.done = False
        self.ok = False
        self.lines: list[str] = []
        self.result: dict | None = None
        self.started = time.time()

    def log(self, line: str) -> None:
        with LOCK:
            self.lines.append(line.rstrip())
            if len(self.lines) > 2000:      # 시연 한 번 분량이면 충분하다
                del self.lines[:500]

    def run(self) -> None:
        for st in self.steps:
            self.stage = st["name"]
            self.log("── %s" % st["name"])
            try:
                p = subprocess.Popen(
                    st["cmd"], cwd=HERE, stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT, text=True, encoding="utf-8",
                    errors="replace", bufsize=1,
                    env={**os.environ, "PYTHONIOENCODING": "utf-8"})
            except Exception as e:  # noqa: BLE001
                self.log("실행 실패: %s" % e)
                self.done = True
                return
            for line in p.stdout:
                self.log(line)
            p.wait()
            if p.returncode != 0:
                self.log("!! %s 단계가 실패했습니다 (코드 %d)" % (st["name"], p.returncode))
                self.done = True
                return
        self.stage = "완료"
        self.ok = True
        self.done = True


def read_result(run_id: str) -> dict:
    """실행 결과를 프론트가 쓰기 좋은 모양으로 추린다."""
    path = os.path.join(HERE, "logs", run_id, "index.json")
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as f:
        idx = json.load(f)
    people = idx.get("personas", [])
    label = {"goal_reached": "달성", "gave_up": "포기", "max_steps": "스텝 소진",
             "loop_detected": "맴돌다 중단", "budget_stop": "예산 상한", "error": "오류"}
    return {
        "run_id": run_id,
        "variant": idx.get("variant"),
        "map_used": idx.get("map_used"),
        "usage": idx.get("usage", {}),
        "summary": {
            "인원": len(people),
            "달성": sum(1 for p in people if p["end_reason"] == "goal_reached"),
            "포기": sum(1 for p in people if p["end_reason"] == "gave_up"),
            "평균 스텝": round(sum(p["steps"] for p in people) / len(people), 1) if people else 0,
        },
        "personas": [{
            "id": p["id"], "label": p.get("label"), "goal": p.get("goal"),
            "traits": p.get("traits"), "steps": p["steps"],
            "end_reason": p["end_reason"], "end_label": label.get(p["end_reason"], p["end_reason"]),
        } for p in people],
    }


def read_trace(run_id: str, persona: str) -> dict:
    """한 사람의 스텝별 기록. 화면 전체는 무거우니 요약만 얹는다."""
    path = os.path.join(HERE, "logs", run_id, "%s.json" % persona)
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as f:
        t = json.load(f)
    steps = []
    for s in t["steps"]:
        snap = s["snapshot"]
        els = snap["elements"]
        steps.append({
            "step": s["step"], "thought": s["thought"], "action": s["action"],
            "outcome": s.get("outcome"), "url": snap["url"], "title": snap["title"],
            "map_miss": s.get("map_miss"), "blocked": bool(s.get("blocked_action")),
            "screen": {
                "요소": len(els),
                "가려짐": sum(1 for e in els if e["occluded"]),
                "저대비": sum(1 for e in els if (e.get("contrast") or 99) < 3.0
                            and not e.get("disabled_attr")),
                "키보드불가": sum(1 for e in els if not e["keyboard_reachable"]),
                "본문대비": snap.get("body_contrast"),
                "본문폰트": snap.get("body_font_size"),
            },
        })
    return {"persona": t["persona"], "variant": t["variant"],
            "end_reason": t["end_reason"], "steps": steps}


class Handler(BaseHTTPRequestHandler):
    server_version = "uxagent/1.0"
    mock = False

    def log_message(self, fmt, *args):      # 기본 로그가 시끄럽다
        pass

    # ── 응답 도우미 ────────────────────────────────────────────
    def _send(self, code: int, payload: dict) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        # 프론트가 다른 포트에서 뜨므로 열어둔다. 로컬 시연 전용이다.
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):                   # noqa: N802 - 표준 라이브러리 규약
        self._send(204, {})

    # ── 조회 ───────────────────────────────────────────────────
    def do_GET(self):                       # noqa: N802
        path = urlparse(self.path).path.rstrip("/")

        if path in ("/api/health", "/api"):
            return self._send(200, {"ok": True, "mock": Handler.mock,
                                    "allowed_hosts": sorted(ALLOWED_HOSTS)})

        if path.startswith("/api/jobs/"):
            parts = path.split("/")
            jid = parts[3] if len(parts) > 3 else ""
            job = JOBS.get(jid)
            if not job:
                return self._send(404, {"error": "그런 작업이 없습니다"})
            if len(parts) > 4 and parts[4] == "result":
                return self._send(200, job.result or {})
            with LOCK:
                lines = list(job.lines)
            return self._send(200, {
                "id": job.id, "stage": job.stage, "done": job.done, "ok": job.ok,
                "elapsed_sec": round(time.time() - job.started, 1),
                "log": lines[-120:], "result": job.result,
            })

        if path.startswith("/api/traces/"):
            parts = path.split("/")
            if len(parts) >= 5:
                return self._send(200, read_trace(parts[3], parts[4]))

        return self._send(404, {"error": "없는 주소입니다"})

    # ── 실행 ───────────────────────────────────────────────────
    def do_POST(self):                      # noqa: N802
        path = urlparse(self.path).path.rstrip("/")
        length = int(self.headers.get("Content-Length") or 0)
        try:
            body = json.loads(self.rfile.read(length) or b"{}")
        except Exception:  # noqa: BLE001
            return self._send(400, {"error": "JSON 을 읽지 못했습니다"})

        if path != "/api/scan":
            return self._send(404, {"error": "없는 주소입니다"})

        base = str(body.get("base") or "http://localhost:8000/ux-testbed")
        if not _allowed(base):
            return self._send(403, {
                "error": "허용되지 않은 주소입니다. 이 데모는 지정된 쇼핑몰만 검사합니다.",
                "allowed_hosts": sorted(ALLOWED_HOSTS)})

        variant = str(body.get("variant") or "buggy")
        count = max(1, min(int(body.get("personas") or 3), 100))
        resurvey = bool(body.get("resurvey"))
        run_id = "web_%s_%s" % (variant, time.strftime("%m%d_%H%M%S"))

        mock = ["--mock"] if Handler.mock else []
        steps = []
        if resurvey:
            steps.append({"name": "답사 — 사이트를 돌아보며 설명서 작성",
                          "cmd": [PY, "-u", "scout.py", "--variant", variant,
                                  "--base", base, "--yes", "--max-steps", "45"] + mock})
        steps.append({"name": "페르소나 %d명 탐색" % count,
                      "cmd": [PY, "-u", "run.py", "--variant", variant, "--base", base,
                              "--limit", str(count), "--run-id", run_id,
                              "--max-usd", "2.0"] + mock})

        jid = uuid.uuid4().hex[:12]
        job = Job(jid, steps)
        JOBS[jid] = job

        def worker():
            job.run()
            job.result = read_result(run_id)

        threading.Thread(target=worker, daemon=True).start()
        return self._send(202, {"job_id": jid, "run_id": run_id,
                                "stages": [s["name"] for s in steps]})


def main() -> int:
    ap = argparse.ArgumentParser(description="프론트용 API 서버 (표준 라이브러리만)")
    ap.add_argument("--port", type=int, default=8100)
    ap.add_argument("--mock", action="store_true",
                    help="LLM 없이 돈다. 프론트 개발용 — 응답 모양은 진짜와 같다")
    args = ap.parse_args()

    Handler.mock = args.mock
    srv = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    print("=" * 58)
    print("  API 서버 http://127.0.0.1:%d%s" % (args.port, "   [모의 — 공짜]" if args.mock else ""))
    print("  검사 허용 호스트: %s" % ", ".join(sorted(ALLOWED_HOSTS)))
    print("=" * 58)
    print("  POST /api/scan          {variant, personas, base, resurvey}")
    print("  GET  /api/jobs/{id}     진행 상황과 로그")
    print("  GET  /api/jobs/{id}/result")
    print("  GET  /api/traces/{run_id}/{persona}")
    print("  GET  /api/health")
    print("\n멈추려면 Ctrl+C")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\n종료했습니다.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
