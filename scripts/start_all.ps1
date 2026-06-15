param(
    [string]$MySqlContainer = "travel-planner-database",
    [string]$VllmContainer = "vllm-qwen3-8b-awq",
    [string]$MySqlPassword = $env:MYSQL_PASSWORD,
    [int]$MySqlTimeoutSeconds = 120,
    [int]$VllmTimeoutSeconds = 900,
    [switch]$SkipInstall,
    [switch]$NoBrowser
)

$ErrorActionPreference = "Stop"

$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"
[Console]::InputEncoding = [System.Text.UTF8Encoding]::new($false)
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)

if ([string]::IsNullOrWhiteSpace($MySqlPassword)) {
    $securePassword = Read-Host "Enter the MySQL root password" -AsSecureString
    $passwordPointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR(
        $securePassword
    )
    try {
        $MySqlPassword = [Runtime.InteropServices.Marshal]::PtrToStringBSTR(
            $passwordPointer
        )
    }
    finally {
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($passwordPointer)
    }
}

$env:MYSQL_PASSWORD = $MySqlPassword

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$RuntimeDir = Join-Path $ProjectRoot ".runtime"
$VenvDir = Join-Path $ProjectRoot ".venv"
$VenvPython = Join-Path $VenvDir "Scripts\python.exe"
$RequirementsFile = Join-Path $ProjectRoot "requirements.txt"
$RequirementsStamp = Join-Path $RuntimeDir "requirements.sha256"

New-Item -ItemType Directory -Path $RuntimeDir -Force | Out-Null

function Write-Step {
    param([string]$Message)
    Write-Host ""
    Write-Host "==> $Message" -ForegroundColor Cyan
}

function Wait-Until {
    param(
        [scriptblock]$Condition,
        [int]$TimeoutSeconds,
        [string]$Description,
        [int]$IntervalSeconds = 2
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        if (& $Condition) {
            Write-Host "$Description is ready." -ForegroundColor Green
            return
        }

        Start-Sleep -Seconds $IntervalSeconds
    }

    throw "Timed out waiting for $Description after $TimeoutSeconds seconds."
}

function Test-TcpPort {
    param(
        [string]$HostName,
        [int]$Port
    )

    $client = [System.Net.Sockets.TcpClient]::new()
    try {
        $connection = $client.ConnectAsync($HostName, $Port)
        return $connection.Wait(500) -and $client.Connected
    }
    catch {
        return $false
    }
    finally {
        $client.Dispose()
    }
}

function Get-ListeningProcessIds {
    param([int]$Port)

    $pattern = "^\s*TCP\s+\S+:$Port\s+\S+\s+LISTENING\s+(\d+)\s*$"
    $processIds = foreach ($line in (& netstat -ano -p tcp)) {
        if ($line -match $pattern) {
            [int]$Matches[1]
        }
    }

    return @($processIds | Sort-Object -Unique)
}

function Ensure-DockerDesktop {
    Write-Step "Checking Docker Desktop"

    $previousPreference = $ErrorActionPreference
    $ErrorActionPreference = "SilentlyContinue"
    & docker info *> $null
    $dockerReady = $LASTEXITCODE -eq 0
    $ErrorActionPreference = $previousPreference
    if ($dockerReady) {
        Write-Host "Docker Desktop is running." -ForegroundColor Green
        return
    }

    $dockerDesktop = Join-Path $env:ProgramFiles "Docker\Docker\Docker Desktop.exe"
    if (-not (Test-Path $dockerDesktop)) {
        throw "Docker Desktop is not running and was not found at: $dockerDesktop"
    }

    Write-Host "Starting Docker Desktop..."
    Start-Process -FilePath $dockerDesktop

    Wait-Until `
        -Description "Docker Desktop" `
        -TimeoutSeconds 180 `
        -IntervalSeconds 3 `
        -Condition {
            $previousPreference = $ErrorActionPreference
            $ErrorActionPreference = "SilentlyContinue"
            & docker info *> $null
            $dockerReady = $LASTEXITCODE -eq 0
            $ErrorActionPreference = $previousPreference
            return $dockerReady
        }
}

function Ensure-Container {
    param([string]$Name)

    & docker inspect $Name *> $null
    if ($LASTEXITCODE -ne 0) {
        throw "Docker container '$Name' does not exist."
    }

    $status = (& docker inspect --format "{{.State.Status}}" $Name).Trim()
    if ($status -ne "running") {
        Write-Host "Starting container '$Name'..."
        & docker start $Name | Out-Null
        if ($LASTEXITCODE -ne 0) {
            throw "Failed to start Docker container '$Name'."
        }
    }
    else {
        Write-Host "Container '$Name' is already running." -ForegroundColor Green
    }
}

function Ensure-PythonEnvironment {
    Write-Step "Checking Python environment"

    if (-not (Test-Path $VenvPython)) {
        Write-Host "Creating virtual environment at .venv..."

        $pythonLauncher = Get-Command py -ErrorAction SilentlyContinue
        if ($pythonLauncher) {
            & py -3 -m venv $VenvDir
        }
        else {
            & python -m venv $VenvDir
        }

        if ($LASTEXITCODE -ne 0 -or -not (Test-Path $VenvPython)) {
            throw "Failed to create the Python virtual environment."
        }
    }

    if ($SkipInstall) {
        Write-Host "Dependency installation skipped."
        return
    }

    $currentHash = (Get-FileHash -Algorithm SHA256 $RequirementsFile).Hash
    $installedHash = if (Test-Path $RequirementsStamp) {
        (Get-Content $RequirementsStamp -Raw).Trim()
    }
    else {
        ""
    }

    if ($currentHash -ne $installedHash) {
        Write-Host "Installing Python dependencies..."
        & $VenvPython -m pip install -r $RequirementsFile
        if ($LASTEXITCODE -ne 0) {
            throw "Dependency installation failed."
        }

        Set-Content -Path $RequirementsStamp -Value $currentHash -Encoding ASCII
    }
    else {
        Write-Host "Python dependencies are up to date." -ForegroundColor Green
    }
}

function Start-PythonService {
    param(
        [string]$Name,
        [string[]]$Arguments,
        [int]$Port
    )

    $existingProcessIds = @(Get-ListeningProcessIds -Port $Port)
    if (Test-TcpPort -HostName "127.0.0.1" -Port $Port) {
        Write-Host "$Name is already listening on port $Port." -ForegroundColor Green
        return
    }

    $stdout = Join-Path $RuntimeDir "$Name.out.log"
    $stderr = Join-Path $RuntimeDir "$Name.err.log"
    $pidFile = Join-Path $RuntimeDir "$Name.pid"

    Write-Host "Starting $Name..."
    $process = Start-Process `
        -FilePath $VenvPython `
        -ArgumentList $Arguments `
        -WorkingDirectory $ProjectRoot `
        -WindowStyle Hidden `
        -RedirectStandardOutput $stdout `
        -RedirectStandardError $stderr `
        -PassThru

    Wait-Until `
        -Description $Name `
        -TimeoutSeconds 60 `
        -Condition {
            if ($process.HasExited) {
                $errorText = if (Test-Path $stderr) {
                    Get-Content $stderr -Raw
                }
                else {
                    "No error log was produced."
                }
                throw "$Name exited during startup.`n$errorText"
            }

            return Test-TcpPort -HostName "127.0.0.1" -Port $Port
        }

    $listeningProcessIds = @(Get-ListeningProcessIds -Port $Port)
    $newProcessIds = @(
        $listeningProcessIds |
            Where-Object { $_ -notin $existingProcessIds }
    )

    if (-not $newProcessIds) {
        $newProcessIds = @($process.Id)
    }

    Set-Content -Path $pidFile -Value $newProcessIds -Encoding ASCII
}

Push-Location $ProjectRoot
try {
    Ensure-DockerDesktop

    Write-Step "Starting Docker containers"
    Ensure-Container -Name $MySqlContainer
    Ensure-Container -Name $VllmContainer

    Write-Step "Waiting for MySQL"
    Wait-Until `
        -Description "MySQL" `
        -TimeoutSeconds $MySqlTimeoutSeconds `
        -Condition {
            & docker exec `
                -e "MYSQL_PWD=$MySqlPassword" `
                $MySqlContainer `
                mysqladmin ping `
                -h 127.0.0.1 `
                -uroot `
                --silent *> $null
            return $LASTEXITCODE -eq 0
        }

    Write-Step "Waiting for vLLM"
    Wait-Until `
        -Description "vLLM" `
        -TimeoutSeconds $VllmTimeoutSeconds `
        -IntervalSeconds 5 `
        -Condition {
            try {
                $response = Invoke-WebRequest `
                    -Uri "http://127.0.0.1:8002/v1/models" `
                    -UseBasicParsing `
                    -TimeoutSec 3
                return $response.StatusCode -eq 200
            }
            catch {
                return $false
            }
        }

    Ensure-PythonEnvironment

    Write-Step "Starting local application services"
    Start-PythonService `
        -Name "weather-agent" `
        -Arguments @("-X", "utf8", "-m", "a2a_agents.weather_agent.server") `
        -Port 9001

    Start-PythonService `
        -Name "ticket-agent" `
        -Arguments @("-X", "utf8", "-m", "a2a_agents.ticket_agent.server") `
        -Port 9002

    Start-PythonService `
        -Name "streamlit" `
        -Arguments @(
            "-X", "utf8",
            "-m", "streamlit", "run", "app.py",
            "--server.headless", "true",
            "--server.address", "127.0.0.1",
            "--server.port", "8501"
        ) `
        -Port 8501

    Write-Host ""
    Write-Host "A2A Travel Planner is ready." -ForegroundColor Green
    Write-Host "Web UI:  http://127.0.0.1:8501"
    Write-Host "Logs:    $RuntimeDir"
    Write-Host "Stop all: .\stop-all.bat"

    if (-not $NoBrowser) {
        Start-Process "http://127.0.0.1:8501"
    }
}
finally {
    Pop-Location
}
