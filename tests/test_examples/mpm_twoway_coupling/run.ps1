# mpm_twoway_coupling — B-route via newton-cli run-script.
# This example needs per-step Python (custom kernels couple particles to rigid bodies)
# so the declarative recipe interpreter cannot express it. The shared
# b_route_runner.py delegates to newton.examples.main() with --viewer null
# --test --num-frames 20, which makes Newton call Example.test_final()
# at the end of the headless run.

$ErrorActionPreference = "Continue"
$here     = Split-Path -Parent $MyInvocation.MyCommand.Path
$projRoot = Resolve-Path (Join-Path $here "..\..\..")
$py       = Join-Path $projRoot ".venv\Scripts\python.exe"
$runner   = Join-Path $here "..\_shared\b_route_runner.py"

$outDir = Join-Path $here "outputs"
New-Item -ItemType Directory -Force -Path $outDir | Out-Null

$logFile = Join-Path $outDir "run.log"

"=== mpm_twoway_coupling via newton-cli run-script (B-route) ===" | Tee-Object -FilePath $logFile

& $py -m newton_cli run-script $runner     --forward mpm_twoway_coupling --forward 20     --artifact-dir $outDir     --timeout 240 --json 2>&1 | Tee-Object -FilePath $logFile -Append
if ($LASTEXITCODE -ne 0) { throw "run-script failed" }

Write-Host "Done."
Get-ChildItem $outDir | Format-Table Name, Length, LastWriteTime -AutoSize
