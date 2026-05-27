$ErrorActionPreference = "Stop"

$dockerCandidates = @(
  "C:\Program Files\Docker\Docker\resources\bin\docker.exe",
  "C:\ProgramData\DockerDesktop\version-bin\docker.exe"
)

$docker = Get-Command docker -ErrorAction SilentlyContinue
if (-not $docker) {
  foreach ($candidate in $dockerCandidates) {
    if (Test-Path $candidate) {
      $env:Path = "$(Split-Path $candidate);$env:Path"
      $docker = Get-Command docker -ErrorAction SilentlyContinue
      break
    }
  }
}

if (-not $docker) {
  Write-Host "Docker CLI not found. Install Docker Desktop first." -ForegroundColor Red
  exit 1
}

docker version
docker compose version

