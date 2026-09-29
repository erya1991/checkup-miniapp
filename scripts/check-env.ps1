$ErrorActionPreference = "Continue"

Write-Host "=== Checkup Miniapp Environment Check ==="

function Check-Command($name, $command) {
    Write-Host "`n[$name]"
    try {
        Invoke-Expression $command
    } catch {
        Write-Host "NOT AVAILABLE: $($_.Exception.Message)" -ForegroundColor Red
    }
}

Check-Command "Git" "git --version"
Check-Command "Python 3.12" "py -3.12 --version"
Check-Command "Node" "node --version"
Check-Command "pnpm" "pnpm --version"
Check-Command "Docker" "docker --version"
Check-Command "Docker Compose" "docker compose version"

Write-Host "`nExpected baseline: Python 3.12.10, Node 24.x, pnpm 12.x, Docker Compose v2."
Write-Host "Review docs/00-baseline/ENVIRONMENT_SETUP.md and stage 00 ACCEPTANCE.md for final validation."
