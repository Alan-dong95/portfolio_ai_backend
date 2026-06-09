# 部署后验收脚本 — 用法: .\scripts\verify_api.ps1 https://your-api.zeabur.app

param(
    [Parameter(Mandatory = $true)]
    [string]$BaseUrl
)

$BaseUrl = $BaseUrl.TrimEnd("/")

function Test-Endpoint {
    param([string]$Name, [string]$Path)
    $url = "$BaseUrl$Path"
    Write-Host "`n==> $Name" -ForegroundColor Cyan
    Write-Host "    GET $url"
    try {
        $response = Invoke-RestMethod -Uri $url -Method Get -TimeoutSec 120
        $response | ConvertTo-Json -Depth 5 -Compress
        return $true
    }
    catch {
        Write-Host "    FAILED: $_" -ForegroundColor Red
        return $false
    }
}

Write-Host "Verifying API at $BaseUrl" -ForegroundColor Green

$ok = $true
$ok = (Test-Endpoint "Health" "/health") -and $ok
$ok = (Test-Endpoint "Portfolio" "/portfolio") -and $ok
$ok = (Test-Endpoint "Feed" "/feed?symbols=BTC-USD&language=zh") -and $ok
$ok = (Test-Endpoint "Brief" "/brief?symbols=BTC-USD&language=zh") -and $ok

if ($ok) {
    Write-Host "`nAll checks passed." -ForegroundColor Green
    exit 0
}

Write-Host "`nSome checks failed — see Zeabur logs and DEPLOY.md." -ForegroundColor Red
exit 1
