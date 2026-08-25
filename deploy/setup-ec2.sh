#!/usr/bin/env bash
#
# EC2(Ubuntu 24.04) 한 번에 세팅하기.
#
#   bash ~/moji-deploy/setup-ec2.sh
#
# 여러 번 돌려도 안전하다(멱등). 코드를 고친 뒤 다시 돌리면 갱신만 된다.
#
# 하는 일:
#   1. nginx / git / python 설치
#   2. 저장소 clone (있으면 pull)
#   3. 파이썬 가상환경 + 의존성
#   4. 썸네일용 크로미움 (--skip-browser 로 건너뛸 수 있음)
#   5. 메모리가 작으면 swap
#   6. SQLite 테이블 생성
#   7. systemd 로 uvicorn 상주
#   8. nginx 설정 적용
#
# 프론트(web/dist)는 로컬에서 구워 올린다 — 이 상자에서 빌드하면
# 1GB 램에서 OOM 으로 죽는다. deploy/upload.ps1 을 쓰면 된다.

set -euo pipefail

REPO_URL="https://github.com/lsb1022/UNITHON2026.git"
APP_DIR="$HOME/UNITHON2026"
SERVER_DIR="$APP_DIR/server"
WEB_ROOT="/var/www/moji"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

SKIP_BROWSER=0
for arg in "$@"; do
  [ "$arg" = "--skip-browser" ] && SKIP_BROWSER=1
done

say() { printf '\n\033[1;34m==> %s\033[0m\n' "$1"; }

# --------------------------------------------------------------------------- #
say "1/8  패키지 설치"
sudo apt-get update -qq
sudo apt-get install -y -qq nginx git python3-venv python3-pip curl

# --------------------------------------------------------------------------- #
say "2/8  저장소"
if [ -d "$APP_DIR/.git" ]; then
  git -C "$APP_DIR" pull --ff-only
else
  git clone --depth 1 "$REPO_URL" "$APP_DIR"
fi

# --------------------------------------------------------------------------- #
say "3/8  파이썬 가상환경"
[ -d "$SERVER_DIR/.venv" ] || python3 -m venv "$SERVER_DIR/.venv"
"$SERVER_DIR/.venv/bin/pip" install -q -U pip
"$SERVER_DIR/.venv/bin/pip" install -q -r "$SERVER_DIR/requirements.txt"

# --------------------------------------------------------------------------- #
say "4/8  썸네일용 크로미움"
if [ "$SKIP_BROWSER" = "1" ]; then
  echo "건너뜀. 썸네일은 미리 넣어 둔 화면 사진으로 떨어진다."
else
  # 둘을 나눠 돌리는 이유가 있다.
  #   - 시스템 라이브러리는 root 여야 깔린다.
  #   - 브라우저 본체는 **반드시 ubuntu 로** 깔아야 한다. sudo 로 깔면
  #     HOME 이 /root 라 /root/.cache/ms-playwright 에 들어가고,
  #     ubuntu 로 도는 uvicorn 이 그 경로를 못 읽어 썸네일이 전부 실패한다.
  sudo "$SERVER_DIR/.venv/bin/python" -m playwright install-deps chromium
  "$SERVER_DIR/.venv/bin/python" -m playwright install chromium
  echo "설치 위치: $(ls -d "$HOME/.cache/ms-playwright"/chromium-* 2>/dev/null | head -1)"
fi

# --------------------------------------------------------------------------- #
say "5/8  swap"
TOTAL_MB=$(awk '/MemTotal/ {print int($2/1024)}' /proc/meminfo)
if [ "$TOTAL_MB" -lt 1800 ] && [ ! -f /swapfile ]; then
  echo "램 ${TOTAL_MB}MB — 크로미움에는 빠듯하다. swap 2GB 를 만든다."
  sudo fallocate -l 2G /swapfile
  sudo chmod 600 /swapfile
  sudo mkswap -q /swapfile
  sudo swapon /swapfile
  grep -q '/swapfile' /etc/fstab || echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab >/dev/null
else
  echo "필요 없음 (램 ${TOTAL_MB}MB)"
fi

# --------------------------------------------------------------------------- #
say "6/8  DB 초기화"
# SQLite 파일은 WorkingDirectory 기준으로 생긴다. 반드시 server/ 에서 돈다.
(cd "$SERVER_DIR" && "$SERVER_DIR/.venv/bin/python" -m app.bootstrap)

# --------------------------------------------------------------------------- #
say "7/8  uvicorn 상주 (systemd)"
sudo cp "$HERE/moji-api.service" /etc/systemd/system/moji-api.service
sudo systemctl daemon-reload
sudo systemctl enable --now moji-api
sudo systemctl restart moji-api

# --------------------------------------------------------------------------- #
say "8/8  nginx"
sudo mkdir -p "$WEB_ROOT"
sudo chown -R ubuntu:ubuntu "$WEB_ROOT"
sudo cp "$HERE/nginx-moji.conf" /etc/nginx/sites-available/moji
sudo ln -sf /etc/nginx/sites-available/moji /etc/nginx/sites-enabled/moji
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl reload nginx

# --------------------------------------------------------------------------- #
say "확인"
sleep 2
printf '  /health          → '; curl -fsS --max-time 10 http://127.0.0.1/health || echo '실패'
printf '\n  /api/runs/active → '; curl -fsS --max-time 10 http://127.0.0.1/api/runs/active || echo '실패'
echo

if [ -f "$WEB_ROOT/index.html" ]; then
  echo
  echo "끝났습니다. http://<이 서버 IP> 로 접속하세요."
else
  echo
  echo "서버는 떴습니다. 아직 화면 파일이 없습니다 —"
  echo "로컬에서 deploy/upload.ps1 을 돌려 web/dist 를 올리세요."
fi
