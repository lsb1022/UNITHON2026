#!/usr/bin/env bash
# 배포가 살아 있는지 확인한다. EC2 안에서 돈다.
#
#   bash ~/moji-deploy/check.sh

DOMAIN="www.unithon-deodmi.site"

# HTTPS 를 붙인 뒤로 http://127.0.0.1 은 301 을 돌려준다. 그것을 실패로 읽으면
# 멀쩡한 서버가 죽은 것처럼 보인다. 인증서가 있으면 정식 주소로 물어보되,
# --resolve 로 이 서버 자신을 가리키게 해서 밖으로 나가지 않는다.
# /etc/letsencrypt/live 는 root 만 들어갈 수 있다. sudo 없이 물으면 늘 "없음"이 된다.
if sudo test -d "/etc/letsencrypt/live/$DOMAIN"; then
  BASE="https://$DOMAIN"
  RESOLVE=(--resolve "$DOMAIN:443:127.0.0.1")
else
  BASE="http://127.0.0.1"
  RESOLVE=()
fi

get()  { curl -fsS  --max-time 20 "${RESOLVE[@]}" "$BASE$1" 2>/dev/null; }
code() { curl -fsS -o /dev/null -w '%{http_code}' --max-time 30 "${RESOLVE[@]}" "$BASE$1" 2>/dev/null || echo 000; }

ok()   { printf '  \033[32m%s\033[0m\n' "$1"; }
fail() { printf '  \033[31m%s\033[0m\n' "$1"; }

echo
echo "확인 대상: $BASE"

echo
echo "서비스"
systemctl is-active --quiet moji-api && ok "moji-api  실행 중" || fail "moji-api  죽어 있음 (sudo journalctl -u moji-api -n 50)"
systemctl is-active --quiet nginx    && ok "nginx     실행 중" || fail "nginx     죽어 있음"

echo
echo "응답"
health=$(get /health)
[ -n "$health" ] && ok "/health           $health" || fail "/health           응답 없음 (nginx→uvicorn 연결 확인)"

# 돌고 있는 실행이 없으면 null 이 정상이다.
active=$(get /api/runs/active)
[ -n "$active" ] && ok "/api/runs/active   $active" || fail "/api/runs/active   응답 없음"

# SPA 폴백이 없으면 여기서 404 가 난다 — 새로고침할 때마다 화면이 깨진다.
c=$(code /settings/plan)
[ "$c" = "200" ] && ok "SPA 폴백           200" || fail "SPA 폴백           $c (try_files 확인)"

if [ -f /var/www/moji/index.html ]; then
  ok "화면 파일          있음"
else
  fail "화면 파일          없음 (로컬에서 upload.ps1 실행)"
fi

echo
echo "썸네일 (없어도 미리 넣어 둔 화면 사진으로 떨어진다)"
c=$(code '/api/thumbnail?url=https%3A%2F%2Fko.wikipedia.org%2F')
[ "$c" = "200" ] && ok "촬영               200" || fail "촬영               $c (playwright 미설치면 404 — 정상)"

if sudo test -d "/etc/letsencrypt/live/$DOMAIN"; then
  echo
  echo "인증서"
  exp=$(sudo openssl x509 -enddate -noout -in "/etc/letsencrypt/live/$DOMAIN/cert.pem" 2>/dev/null | cut -d= -f2)
  left=$(( ( $(date -d "$exp" +%s) - $(date +%s) ) / 86400 ))
  [ "$left" -gt 20 ] && ok "만료까지 ${left}일 ($exp)" || fail "만료까지 ${left}일 — 갱신 확인 필요"
  systemctl is-enabled --quiet certbot.timer && ok "자동 갱신 예약됨" || fail "자동 갱신 꺼져 있음"
fi
echo
