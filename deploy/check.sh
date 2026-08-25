#!/usr/bin/env bash
# 배포가 살아 있는지 확인한다. EC2 안에서 돈다.
#
#   bash ~/moji-deploy/check.sh

ok()   { printf '  \033[32m%s\033[0m\n' "$1"; }
fail() { printf '  \033[31m%s\033[0m\n' "$1"; }

echo
echo "서비스"
systemctl is-active --quiet moji-api && ok "moji-api  실행 중" || fail "moji-api  죽어 있음 (sudo journalctl -u moji-api -n 50)"
systemctl is-active --quiet nginx    && ok "nginx     실행 중" || fail "nginx     죽어 있음"

echo
echo "응답"
health=$(curl -fsS --max-time 10 http://127.0.0.1/health 2>/dev/null || true)
[ -n "$health" ] && ok "/health           $health" || fail "/health           응답 없음 (nginx→uvicorn 연결 확인)"

active=$(curl -fsS --max-time 10 http://127.0.0.1/api/runs/active 2>/dev/null || true)
# 돌고 있는 실행이 없으면 null 이 정상이다.
[ -n "$active" ] && ok "/api/runs/active   $active" || fail "/api/runs/active   응답 없음"

code=$(curl -fsS -o /dev/null -w '%{http_code}' --max-time 10 http://127.0.0.1/settings/plan 2>/dev/null || echo 000)
# SPA 폴백이 없으면 여기서 404 가 난다 — 새로고침할 때마다 화면이 깨진다.
[ "$code" = "200" ] && ok "SPA 폴백           200" || fail "SPA 폴백           $code (try_files 확인)"

if [ -f /var/www/moji/index.html ]; then
  ok "화면 파일          있음"
else
  fail "화면 파일          없음 (로컬에서 upload.ps1 실행)"
fi

echo
echo "썸네일 (없어도 미리 넣어 둔 화면 사진으로 떨어진다)"
shot=$(curl -fsS -o /dev/null -w '%{http_code}' --max-time 30 \
  'http://127.0.0.1/api/thumbnail?url=https%3A%2F%2Fko.wikipedia.org%2F' 2>/dev/null || echo 000)
[ "$shot" = "200" ] && ok "촬영               200" || fail "촬영               $shot (playwright 미설치면 404 — 정상)"
echo
