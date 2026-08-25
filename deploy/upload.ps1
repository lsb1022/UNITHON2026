# 로컬(Windows) -> EC2 업로드.
#
#   처음 한 번 (서버 세팅까지):
#     .\deploy\upload.ps1 -Ip 3.34.xxx.xxx -Key C:\keys\moji.pem -Setup
#
#   그 뒤 화면만 다시 올릴 때:
#     .\deploy\upload.ps1 -Ip 3.34.xxx.xxx -Key C:\keys\moji.pem
#
# 하는 일:
#   1. dev 서버가 떠 있으면 끈다 (안 끄면 빌드가 EPERM 으로 죽는다)
#   2. web 을 배포용으로 빌드하고 결과를 검사한다
#   3. deploy/ 스크립트를 올린다
#   4. -Setup 이면 EC2 세팅을 돌린다
#   5. dist 를 /var/www/moji 로 올린다
#   6. 살아 있는지 확인한다

param(
    [Parameter(Mandatory = $true)][string]$Ip,
    [Parameter(Mandatory = $true)][string]$Key,
    [string]$User = 'ubuntu',
    [switch]$Setup,
    [switch]$SkipBuild
)

$ErrorActionPreference = 'Stop'
$root   = Split-Path -Parent $PSScriptRoot
$web    = Join-Path $root 'web'
$dist   = Join-Path $web 'dist'
$remote = $User + '@' + $Ip

function Step($msg) { Write-Host "`n==> $msg" -ForegroundColor Cyan }
function Ssh($cmd)  { ssh -i $Key -o StrictHostKeyChecking=accept-new $remote $cmd }

if (-not (Test-Path $Key)) { throw "키 파일이 없습니다: $Key" }

# --------------------------------------------------------------------------- #
if (-not $SkipBuild) {
    Step '개발 서버 정리'
    # Vite 가 rolldown 네이티브 파일(.node)을 잡고 있으면 빌드가 EPERM 으로 죽는다.
    # Windows 는 사용 중인 파일을 지우지 못한다.
    $stale = @(Get-CimInstance Win32_Process -Filter "Name='node.exe'" |
               Where-Object { $_.CommandLine -like '*UNITHON2026*' })
    if ($stale.Count -gt 0) {
        $stale | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
        Write-Host "  node 프로세스 $($stale.Count)개 종료"
        Start-Sleep -Milliseconds 800
    }
    else { Write-Host '  없음' }

    Step '빌드'
    Push-Location $web
    try {
        npm run build
        if ($LASTEXITCODE -ne 0) { throw '빌드 실패' }
    }
    finally { Pop-Location }
}

if (-not (Test-Path (Join-Path $dist 'index.html'))) { throw "dist 가 없습니다: $dist" }

# 상대경로로 빌드됐는지 확인한다. localhost:8000 이 남아 있으면 배포본에서
# 방문자 자기 PC 를 부르게 되어 썸네일과 실행중 배너가 죽는다.
Step '빌드 결과 검사'
$leak = Select-String -Path (Join-Path $dist 'assets\*.js') -Pattern 'localhost:8000' -SimpleMatch -List
if ($leak) {
    throw ' 번들에 localhost:8000 이 남아 있습니다. web/.env.production 의 VITE_API_BASE= (빈 값) 를 확인하세요.'
}
Write-Host '  API 주소 상대경로 OK'

# --------------------------------------------------------------------------- #
Step '배포 스크립트 업로드'
Ssh 'mkdir -p ~/moji-deploy'
scp -i $Key -r "$PSScriptRoot\*" ($remote + ':~/moji-deploy/')
# Windows 에서 올린 파일은 줄바꿈이 CRLF 라 bash 가 첫 줄부터 못 읽는다.
Ssh 'sed -i "s/\r//" ~/moji-deploy/setup-ec2.sh ~/moji-deploy/check.sh ~/moji-deploy/moji-api.service ~/moji-deploy/nginx-moji.conf'

if ($Setup) {
    Step 'EC2 세팅 (몇 분 걸립니다)'
    Ssh 'bash ~/moji-deploy/setup-ec2.sh'
    if ($LASTEXITCODE -ne 0) { throw 'EC2 세팅 실패' }
}

# --------------------------------------------------------------------------- #
Step '화면 파일 업로드'
# 옛 자산이 남아 있으면 용량만 먹는다. 통째로 비우고 올린다.
Ssh 'sudo mkdir -p /var/www/moji && sudo chown -R $USER:$USER /var/www/moji && rm -rf /var/www/moji/*'
scp -i $Key -r "$dist\*" ($remote + ':/var/www/moji/')

# --------------------------------------------------------------------------- #
Step '확인'
Ssh 'bash ~/moji-deploy/check.sh'

Write-Host "`n완료. http://$Ip" -ForegroundColor Green
