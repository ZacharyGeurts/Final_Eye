# Final_Eye Windows install
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root
$Ver = if (Test-Path VERSION) { (Get-Content VERSION -Raw).Trim() } else { "unknown" }

$py = if (Get-Command py -ErrorAction SilentlyContinue) { "py -3" } else { "python" }
Write-Host "Final_Eye v$Ver — installing dependencies…"
Invoke-Expression "$py -m pip install -r requirements.txt"
Invoke-Expression "$py zocr_security.py seal"
New-Item -ItemType Directory -Force -Path data, out, addons | Out-Null
Write-Host "Done. Run Start-FinalEye.bat or:"
Write-Host "  $py gui\app.py"