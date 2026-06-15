param(
    [string]$MySqlContainer = "travel-planner-database",
    [string]$VllmContainer = "vllm-qwen3-8b-awq",
    [switch]$StopContainers
)

$ErrorActionPreference = "Continue"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$RuntimeDir = Join-Path $ProjectRoot ".runtime"
$services = @("streamlit", "ticket-agent", "weather-agent")

foreach ($service in $services) {
    $pidFile = Join-Path $RuntimeDir "$service.pid"
    if (-not (Test-Path $pidFile)) {
        continue
    }

    $processIds = @(
        Get-Content $pidFile -ErrorAction SilentlyContinue |
            Where-Object { $_ -match "^\d+$" }
    )

    foreach ($serviceProcessId in $processIds) {
        if (Get-Process -Id $serviceProcessId -ErrorAction SilentlyContinue) {
            Write-Host "Stopping $service (PID $serviceProcessId)..."
            & taskkill.exe /PID $serviceProcessId /T /F 2>$null | Out-Null
        }
    }

    Remove-Item -LiteralPath $pidFile -Force -ErrorAction SilentlyContinue
}

if ($StopContainers) {
    foreach ($container in @($VllmContainer, $MySqlContainer)) {
        $status = & docker inspect --format "{{.State.Status}}" $container 2>$null
        if ($LASTEXITCODE -eq 0 -and $status.Trim() -eq "running") {
            Write-Host "Stopping Docker container '$container'..."
            & docker stop $container | Out-Null
        }
    }
}

Write-Host "A2A Travel Planner services stopped." -ForegroundColor Green
