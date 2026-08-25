# 배포 (AWS EC2)

## 현재 배포

| | |
| --- | --- |
| 주소 | http://15.164.99.220 |
| 도메인 | `unithon-deodmi.site` · `www.unithon-deodmi.site` (DNS A 레코드 연결 필요) |
| 인스턴스 | Ubuntu 24.04.4 LTS · 2 vCPU · 1.9GB |
| 키 | `unithon2026.pem` |

재배포는 아래 `upload.ps1` 한 줄. 상태 확인은
`ssh -i <키> ubuntu@15.164.99.220 "bash ~/moji-deploy/check.sh"`.


프론트(`web/dist`)와 서버(`server/`, FastAPI)를 **한 대의 EC2**에 올린다.

```
브라우저 ──► nginx :80
               ├─ /      ──► /var/www/moji     (web/dist)
               └─ /api/  ──► 127.0.0.1:8000    (uvicorn)
```

화면과 API 를 **같은 오리진**으로 묶는 것이 요점이다. 그래서 브라우저가 CORS 를
따지지 않고, `server/app/main.py` 의 허용 목록을 건드릴 일도 없다.

## 먼저 알아둘 것 — 지금 앱은 "목업 모드"로 돈다

`web/.env.production` 이 `VITE_MOCK=1` 이다. 이게 로컬에서 보던 그 상태다.
서버가 실제로 하는 일은 두 가지뿐이다.

| 하는 일 | 엔드포인트 |
| --- | --- |
| 썸네일 촬영 | `/api/thumbnail` |
| 실행중 배너 | `/api/runs/active` |

나머지(프로젝트·A/B·설정·크레딧)는 전부 프론트 목업이 답한다.
`VITE_MOCK=0` 으로 바꾸면 **A/B 테스트·설정·크레딧 화면이 404 로 죽는다** —
그 엔드포인트들은 아직 서버에 없다.

배포해도 **안 되는 것**(로컬과 동일):

- **테스트 하기** → 422. 실제 탐색을 도는 파이프라인이 이 저장소에 없다.
- **크레딧 충전 / 플랜 변경 / 프로필 저장** → 안내 문구만. 결제·계정 서버가 없다.
- **만든 프로젝트·A/B** → 브라우저 localStorage. 기기가 바뀌면 안 보인다.

---

## 직접 해야 하는 것

자동화할 수 없는 것은 AWS 콘솔 작업뿐이다.

1. **EC2 인스턴스 생성**
   - AMI: **Ubuntu Server 24.04 LTS**
   - 타입: **t3.small** 권장 (t3.micro 도 되지만 크로미움에 빠듯하다 —
     스크립트가 알아서 swap 2GB 를 만든다)
   - 스토리지: 16GB 이상 (크로미움이 ~450MB)
2. **키 페어** 다운로드 → 예) `C:\keys\moji.pem`
3. **보안 그룹 인바운드**
   | 포트 | 소스 | 용도 |
   | --- | --- | --- |
   | 22 | 내 IP | ssh |
   | 80 | 0.0.0.0/0 | http |
   | 443 | 0.0.0.0/0 | https (도메인 있을 때) |

   **8000 은 열지 않는다.** nginx 만 통과시킨다.
4. **퍼블릭 IP** 를 적어둔다.

---

## 배포

로컬(Windows PowerShell)에서 **한 줄**이면 된다.

```powershell
cd C:\Users\lsbop\Documents\GitHub\UNITHON2026
.\deploy\upload.ps1 -Ip <퍼블릭IP> -Key C:\keys\moji.pem -Setup
```

`-Setup` 은 처음 한 번만. 스크립트가 하는 일:

1. 떠 있는 dev 서버를 끈다 (안 끄면 빌드가 `EPERM` 으로 죽는다)
2. `web` 을 배포용으로 빌드하고, 번들에 `localhost:8000` 이 남았는지 검사한다
3. `deploy/` 를 EC2 로 올리고 CRLF 를 없앤다
4. `setup-ec2.sh` 를 돌린다 (아래 참고)
5. `dist` 를 `/var/www/moji` 로 올린다
6. `check.sh` 로 살아 있는지 확인한다

끝나면 `http://<퍼블릭IP>`.

### 두 번째부터

```powershell
.\deploy\upload.ps1 -Ip <퍼블릭IP> -Key C:\keys\moji.pem
```

서버 코드를 고쳤다면:

```powershell
ssh -i C:\keys\moji.pem ubuntu@<IP> "cd ~/UNITHON2026 && git pull && sudo systemctl restart moji-api"
```

---

## 파일

| 파일 | 하는 일 |
| --- | --- |
| `upload.ps1` | 로컬에서 실행. 빌드 → 업로드 → 확인 |
| `setup-ec2.sh` | EC2 세팅. 여러 번 돌려도 안전(멱등) |
| `check.sh` | 배포가 살아 있는지 확인 |
| `moji-api.service` | uvicorn 을 systemd 로 상주 |
| `nginx-moji.conf` | 정적 서빙 + `/api` 프록시 + SPA 폴백 |

`setup-ec2.sh` 는 저장소 clone → venv → 의존성 → 크로미움 → swap →
SQLite 테이블 → systemd → nginx 순으로 돈다.
크로미움을 건너뛰려면 `bash ~/moji-deploy/setup-ec2.sh --skip-browser`.
그래도 앱은 돈다 — 썸네일이 미리 넣어 둔 화면 사진으로 떨어질 뿐이다.

---

## HTTPS (도메인이 있을 때만)

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

IP 만으로는 인증서를 받을 수 없다. 데모라면 HTTP 로 둬도 동작한다 —
페이지가 HTTP 여도 위키백과·GitHub Pages 를 https 로 불러오는 것은 막히지 않는다.

---

## 문제가 생기면

```bash
ssh -i C:\keys\moji.pem ubuntu@<IP>
bash ~/moji-deploy/check.sh          # 어디가 죽었는지
sudo journalctl -u moji-api -n 50    # 서버 로그
sudo tail -50 /var/log/nginx/error.log
```

| 증상 | 원인 |
| --- | --- |
| 화면은 뜨는데 새로고침하면 404 | nginx SPA 폴백(`try_files`) |
| 썸네일이 전부 회색 판 | 크로미움 미설치 — 폴백 사진이 없는 주소다 |
| 썸네일이 전부 폴백 사진 | 크로미움 미설치. 정상 동작이다 |
| 배포했는데 옛 화면 | `index.html` 캐시 — 강력 새로고침(Ctrl+Shift+R) |
| `npm ci` 가 `EPERM` | dev 서버가 파일을 잡고 있다. `upload.ps1` 이 알아서 끈다 |
