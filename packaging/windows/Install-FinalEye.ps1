# Final_Eye v1.0 Windows install
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

$py = if (Get-Command py -ErrorAction SilentlyContinue) { "py -3" } else { "python" }
Write-Host "Final_Eye v1.0 — installing dependencies…"
Invoke-Expression "$py -m pip install -r requirements.txt"
Invoke-Expression "$py zocr_security.py seal"
New-Item -ItemType Directory -Force -Path data, out, addons | Out-Null
Write-Host "Done. Run Start-FinalEye.bat or:"
Write-Host "  $py gui\app.py"