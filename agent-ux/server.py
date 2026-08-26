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
from urllib.parse import quote, unquote, urlparse

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
# 이 데모가 검사해도 되는 곳. 남의 사이트를 마구 두들기지 않으려고 좁혀 둔다.
# 공개 문서 사이트는 예시로 열어 둔다 — 실제로 여기서 돌려 본 곳이다.
ALLOWED_HOSTS = {"localhost", "127.0.0.1", "lsb1022.github.io",
                 "ko.wikipedia.org", "webscraper.io"}

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
        self.run_id = ""
        self.total = 0
        self.title = ""
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


def done_count(run_id: str) -> int:
    """끝난 사람 수 = logs/{run_id}/ 에 쌓인 개인 기록 파일 수.

    한 명이 끝날 때마다 즉시 저장하므로 이 값이 곧 진행률이다.
    시간으로 어림잡지 않는다 — 어림값은 화면에 그럴듯하게 흐르지만 거짓이다.
    """
    d = os.path.join(HERE, "logs", run_id)
    if not os.path.isdir(d):
        return 0
    return len([f for f in os.listdir(d)
                if f.startswith("P") and f.endswith(".json")])


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


SHOTS_ROOT = os.path.join(HERE, "shots_web")


def shot_runs() -> list[str]:
    """스크린샷이 남은 실행들. 최근 것이 앞에 온다."""
    if not os.path.isdir(SHOTS_ROOT):
        return []
    ds = [d for d in os.listdir(SHOTS_ROOT)
          if os.path.isdir(os.path.join(SHOTS_ROOT, d))]
    return sorted(ds, key=lambda d: os.path.getmtime(os.path.join(SHOTS_ROOT, d)),
                  reverse=True)


def shot_files(run_id: str) -> list[str]:
    d = os.path.join(SHOTS_ROOT, run_id)
    if not os.path.isdir(d):
        return []
    return sorted(f for f in os.listdir(d) if f.endswith(".png"))


GALLERY = """<!doctype html><html lang="ko"><head><meta charset="utf-8">
<title>답사자가 본 화면</title>
<style>
 body{margin:0;background:#11161c;color:#e6ebf0;
   font-family:system-ui,"Malgun Gothic",sans-serif}
 header{padding:1rem 1.2rem;border-bottom:1px solid #28313b}
 h1{margin:0;font-size:1.05rem}
 p{margin:.35rem 0 0;color:#8b95a0;font-size:.85rem;max-width:70ch}
 .grid{display:grid;gap:1rem;padding:1.2rem;
   grid-template-columns:repeat(auto-fill,minmax(320px,1fr))}
 figure{margin:0;background:#171d25;border:1px solid #28313b;border-radius:6px;
   overflow:hidden}
 img{width:100%%;display:block;background:#fff}
 figcaption{padding:.45rem .6rem;font-size:.78rem;color:#8b95a0;
   font-family:ui-monospace,monospace}
 .empty{padding:2rem 1.2rem;color:#8b95a0}
 a{color:#69b4d6}
</style></head><body>
<header>
  <h1>답사자가 본 화면 — %(run)s</h1>
  <p>첫 페르소나(답사자)가 스텝마다 찍은 스크린샷입니다. 이 그림들로 사이트
  설명서를 만들고, <b>뒤따르는 페르소나들은 이미지를 한 장도 쓰지 않습니다</b> —
  설명서와 계산된 수치(대비·좌표·가림)만 텍스트로 받습니다.</p>
  <p>다른 실행: %(others)s</p>
</header>
%(body)s
</body></html>"""


class Handler(BaseHTTPRequestHandler):
    server_version = "uxagent/1.0"
    mock = False
    personas = 3
    variant = "buggy"

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

        # 답사 스크린샷 갤러리 (임시 확인용). 브라우저로 바로 연다.
        if path == "/shots" or path.startswith("/shots/"):
            # 주소는 인코딩돼서 온다. 되돌리지 않으면 한글이 섞인 폴더를 못 찾는다.
            parts = [unquote(x) for x in path.split("/") if x]
            runs = shot_runs()
            run = parts[1] if len(parts) > 1 else (runs[0] if runs else "")
            if len(parts) > 2:                       # /shots/{run}/{file} — 이미지 자체
                fp = os.path.join(SHOTS_ROOT, parts[1], parts[2])
                if os.path.isfile(fp) and fp.endswith(".png"):
                    data = open(fp, "rb").read()
                    self.send_response(200)
                    self.send_header("Content-Type", "image/png")
                    self.send_header("Content-Length", str(len(data)))
                    self.send_header("Access-Control-Allow-Origin", "*")
                    self.end_headers()
                    self.wfile.write(data)
                    return
                return self._send(404, {"error": "그런 그림이 없습니다"})

            files = shot_files(run)
            if not files:
                body = ('<div class="empty">아직 스크린샷이 없습니다. '
                        '답사가 끝나면 여기에 쌓입니다.</div>')
            else:
                body = '<div class="grid">' + "".join(
                    '<figure><img loading="lazy" src="/shots/%s/%s" alt="%s">'
                    '<figcaption>%s</figcaption></figure>'
                    % (quote(run), quote(f), f, f)
                    for f in files) + "</div>"
            others = " · ".join('<a href="/shots/%s">%s</a>' % (quote(r), r)
                                for r in runs[:6]) or "없음"
            html = (GALLERY % {"run": run or "(없음)", "body": body,
                               "others": others}).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(html)))
            self.end_headers()
            self.wfile.write(html)
            return

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

        # 프론트의 실행중 화면이 2초마다 부른다. 가장 최근 작업 하나를 알린다.
        if path == "/api/runs/active":
            live = [j for j in JOBS.values() if not j.done]
            job = live[-1] if live else None
            if job is None:
                return self._send(200, None)
            done = done_count(job.run_id)
            return self._send(200, {
                "run_id": job.id,
                # 프로젝트 이름을 여기서 지어내면 안 된다. 어느 프로젝트를 돌리든
                # "MOJI STORE" 가 떴다 — 위키백과를 돌려도 그랬다.
                # 실행을 시작할 때 프론트가 보낸 값을 그대로 되돌려준다.
                "project_id": getattr(job, "project_id", "") or "",
                "project_name": getattr(job, "project_name", "") or "실행 중",
                # ActiveRun 스키마에는 단계 칸이 없다. 답사에만 몇 분이 걸리는데
                # 그동안 0% 만 보이면 멈춘 것처럼 읽힌다. 이름에 단계를 실어 보낸다.
                "test_name": "%s · %s" % (job.stage, job.title),
                "done": done,
                "total": job.total,
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

        # 프론트의 '테스트 하기' 버튼. 답사부터 실제로 돌린다.
        if path.startswith("/api/tests/") and path.endswith("/runs"):
            return self._start(body, from_web=True)

        # 미션 검증. 규칙으로 먼저 거르고 남은 것만 Gemini 에게 묻는다.
        # 키는 서버에만 둔다 — 브라우저에서 직접 부르면 키가 번들에 실린다.
        if path == "/api/missions/analyze":
            return self._analyze(body)

        if path != "/api/scan":
            return self._send(404, {"error": "없는 주소입니다"})

        return self._start(body, from_web=False)

    def _analyze(self, body: dict):
        from uxagent import mission
        from uxagent.llm import Usage, build_client

        goal = str(body.get("prompt") or body.get("goal") or "")

        # 규칙에서 걸리면 여기서 끝. 모델을 부르지 않는다.
        if mission.rule_issues(goal):
            return self._send(200, mission.analyze(goal, mock=True))

        site_map = None
        variant = str(body.get("variant") or Handler.variant)
        mp = os.path.join(config.MAPS_DIR, "site_map_%s.json" % variant)
        if os.path.exists(mp):
            with open(mp, encoding="utf-8") as f:
                site_map = json.load(f)

        if Handler.mock or not config.api_key(config.role_provider("goals")):
            return self._send(200, mission.analyze(goal, site_map=site_map, mock=True))

        usage = Usage()
        try:
            pname = config.role_provider("goals")
            out = mission.analyze(goal, site_map=site_map,
                                  client=build_client(pname),
                                  models=config.models("goals", pname),
                                  usage=usage, mock=False)
        except Exception as e:  # noqa: BLE001
            # 모델이 죽어도 화면은 살아야 한다. 규칙 층 결과로 물러선다.
            out = mission.analyze(goal, site_map=site_map, mock=True)
            out["note"] = "모델 확인은 건너뛰었습니다 (%s)" % str(e)[:80]
        out["usage"] = usage.as_dict()
        return self._send(200, out)

    def _start(self, body: dict, from_web: bool):
        # 프론트가 어떤 프로젝트에서 눌렀는지 함께 보낸다. 예전에는 빈 요청이 와서
        # 어느 화면에서 눌러도 서버 기본값(테스트베드 결함판)이 돌았다 — 위키백과
        # 프로젝트를 만들고 눌러도 "MOJI STORE / 코튼 셔츠 주문 완주"가 떴다.
        url = str(body.get("url") or "").strip()
        goal = str(body.get("goal") or "").strip()
        expect = str(body.get("expect") or "").strip()
        base = str(body.get("base") or "http://localhost:8000/ux-testbed")

        if not _allowed(url or base):
            return self._send(403, {
                "error": "허용되지 않은 주소입니다. 이 데모는 지정된 사이트만 검사합니다.",
                "allowed_hosts": sorted(ALLOWED_HOSTS)})

        variant = str(body.get("variant") or Handler.variant)
        count = max(1, min(int(body.get("personas") or Handler.personas), 100))
        title = str(body.get("test_name") or "코튼 셔츠 주문 완주")
        resurvey = bool(body.get("resurvey", from_web))

        # 우리 테스트베드는 변형 이름으로, 남의 사이트는 주소로 부른다.
        if url:
            target = ["--url", url]
            stem = url.split("//")[-1].split("/")[0]
        else:
            target = ["--variant", variant, "--base", base]
            stem = variant
        run_id = "web_%s_%s" % (stem.replace(".", "_"), time.strftime("%m%d_%H%M%S"))

        mock = ["--mock"] if Handler.mock else []
        steps = []
        if resurvey:
            # 답사자가 본 것을 남긴다. 모델에 보내고 버리면 "무엇을 보고 이 설명서를
            # 썼는가"를 나중에 아무도 확인할 수 없다. 페르소나는 이미지를 안 쓰므로
            # 스크린샷은 여기서만 쌓인다.
            steps.append({"name": "1단계 · 첫 페르소나가 사이트를 둘러보며 설명서를 씁니다",
                          "cmd": [PY, "-u", "survey.py"] + target
                                 + ["--yes", "--max-pages", "6",
                                    "--shots-dir", os.path.join("shots_web", run_id)]
                                 + mock})

        # 화면에서 정한 연령대·성별 비율. 묻고서 안 쓰면 없느니만 못하다 —
        # 예전에는 앞에서부터 N명을 집어서, "20대 여성 40명"으로 맞춰도 실제로
        # 도는 사람은 그것과 아무 상관이 없었다.
        specs = body.get("persona_specs") or []
        pick_path = ""
        if isinstance(specs, list) and specs:
            os.makedirs("logs", exist_ok=True)
            pick_path = os.path.join("logs", "pick_%s.json" % run_id)
            with open(pick_path, "w", encoding="utf-8") as f:
                json.dump(specs, f, ensure_ascii=False)
            count = sum(int(x.get("total") or 0) for x in specs
                        if x.get("enabled") is not False)
            count = max(1, min(count, 100))

        run_cmd = [PY, "-u", "run.py"] + target + [
            "--run-id", run_id, "--max-usd", "2.0"]
        if pick_path:
            run_cmd += ["--pick", pick_path]
        else:
            run_cmd += ["--limit", str(count)]
        # 미션과 근거는 실행할 때만 갈아 끼운다. personas.json 은 건드리지 않는다.
        if goal:
            run_cmd += ["--goal", goal]
        if expect:
            run_cmd += ["--expect", expect]
        # 지도가 없는 사이트면 답사 없이도 돌 수 있게 한다.
        if not resurvey and url:
            run_cmd += ["--no-map"]
        steps.append({"name": "2단계 · 페르소나 %d명이 그 설명서를 읽고 미션을 수행합니다" % count,
                      "cmd": run_cmd + mock})

        jid = uuid.uuid4().hex[:12]
        job = Job(jid, steps)
        job.run_id = run_id
        job.total = count
        job.title = title
        # 화면이 "지금 무엇을 돌리고 있나"를 정확히 말할 수 있게 붙여 둔다.
        job.project_id = str(body.get("project_id") or "")
        job.project_name = str(body.get("project_name") or (
            url.split("//")[-1].split("/")[0] if url else variant))
        job.target = url or base
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
    ap.add_argument("--personas", type=int, default=3,
                    help="프론트에서 실행할 때 돌릴 인원. 시연은 2~3명이 알맞다 "
                         "(한 명당 1~2분)")
    ap.add_argument("--variant", default="buggy", choices=("clean", "buggy", "flawed"),
                    help="프론트에서 실행할 때 검사할 판")
    args = ap.parse_args()

    Handler.mock = args.mock
    Handler.personas = args.personas
    Handler.variant = args.variant
    srv = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    print("=" * 58)
    print("  API 서버 http://127.0.0.1:%d%s" % (args.port, "   [모의 — 공짜]" if args.mock else ""))
    print("  검사 허용 호스트: %s" % ", ".join(sorted(ALLOWED_HOSTS)))
    print("=" * 58)
    print("  POST /api/scan                  {variant, personas, base, resurvey}")
    print("  POST /api/tests/{id}/runs       프론트의 '테스트 하기' (답사부터)")
    print("  GET  /api/runs/active           진행률 (끝난 기록 파일 수)")
    print("  GET  /api/jobs/{id}     진행 상황과 로그")
    print("  GET  /api/jobs/{id}/result")
    print("  GET  /api/traces/{run_id}/{persona}")
    print("  GET  /api/health")
    print("  GET  /shots                     답사자가 본 화면 (임시 갤러리)")
    print("\n멈추려면 Ctrl+C")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\n종료했습니다.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
