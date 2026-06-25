# Final_Eye v1.0 — start server
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root
$py = if (Get-Command py -ErrorAction SilentlyContinue) { "py -3" } else { "python" }
Write-Host "Final_Eye http://127.0.0.1:9479/"
Invoke-Expression "$py gui\app.py"