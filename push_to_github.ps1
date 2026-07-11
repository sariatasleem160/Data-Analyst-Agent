#!/usr/bin/env pwsh
# Push project to GitHub — all commits authored by sariatasleem160 only
$ErrorActionPreference = "Stop"
$proj = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $proj

$git = Join-Path $proj ".git-portable\cmd\git.exe"
if (-not (Test-Path $git)) { throw "Portable git not found. Run setup first." }

$authorName = "sariatasleem160"
$authorEmail = "sariatasleem160@users.noreply.github.com"
$author = "$authorName <$authorEmail>"

$env:GIT_AUTHOR_NAME = $authorName
$env:GIT_AUTHOR_EMAIL = $authorEmail
$env:GIT_COMMITTER_NAME = $authorName
$env:GIT_COMMITTER_EMAIL = $authorEmail

& $git branch -M main 2>$null
& $git remote remove origin 2>$null
& $git remote add origin "https://github.com/sariatasleem160/Data-Analyst-Agent.git"

$files = @(
    ".gitignore",
    ".env.example",
    "requirements.txt",
    "README.md",
    "docs/architecture.md",
    "data/sales.csv",
    "tool_schemas.py",
    "tools.py",
    "planner.py",
    "memory.py",
    "agent.py",
    "mcp_server.py",
    "app.py",
    "evaluate.py",
    "injection_tests.py",
    "test_tools.py",
    "run.bat",
    "start_server.bat",
    "results/charts/.gitkeep"
)

foreach ($f in $files) {
    if (Test-Path $f) {
        & $git add $f
        & $git commit --author=$author -m "Add $f"
        Write-Host "Committed: $f"
    }
}

Write-Host "`nPushing to GitHub..."
& $git push -u origin main
Write-Host "Done: https://github.com/sariatasleem160/Data-Analyst-Agent"
