$ErrorActionPreference = "Stop"

$installer = "D:\zuoyiqing\DockerDesktopInstaller.exe"
$expectedSha256 = "72F5AE091B90FFDA86BBE721B484342B34E347586111E049E7C157D3E37D7E27"
$url = "https://desktop.docker.com/win/main/amd64/225177/Docker%20Desktop%20Installer.exe"

function Test-Admin {
  $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
  $principal = New-Object Security.Principal.WindowsPrincipal($identity)
  return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

if (-not (Test-Admin)) {
  Write-Host "This installer must run as Administrator. Relaunching with UAC..." -ForegroundColor Yellow
  Start-Process powershell.exe -Verb RunAs -ArgumentList @(
    "-ExecutionPolicy", "Bypass",
    "-File", "`"$PSCommandPath`""
  )
  exit 0
}

if (-not (Test-Path $installer)) {
  Write-Host "Downloading Docker Desktop installer..."
  curl.exe -L --retry 5 --retry-delay 5 -o $installer $url
}

$hash = (Get-FileHash -LiteralPath $installer -Algorithm SHA256).Hash
if ($hash -ne $expectedSha256) {
  Write-Host "Installer hash mismatch. Re-downloading with resume..." -ForegroundColor Yellow
  curl.exe -L -C - --retry 5 --retry-delay 5 -o $installer $url
  $hash = (Get-FileHash -LiteralPath $installer -Algorithm SHA256).Hash
}

if ($hash -ne $expectedSha256) {
  throw "Docker installer hash mismatch after download. Expected $expectedSha256, got $hash"
}

Write-Host "Installing Docker Desktop..."
$process = Start-Process -FilePath $installer -ArgumentList @(
  "install",
  "--quiet",
  "--accept-license",
  "--backend=wsl-2"
) -Wait -PassThru

if ($process.ExitCode -ne 0) {
  throw "Docker Desktop installer failed with exit code $($process.ExitCode)"
}

Write-Host "Docker Desktop installed. A Windows restart may be required before docker works." -ForegroundColor Green

