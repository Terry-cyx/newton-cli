# mpm_viscous — viscous fluid draining through a funnel via MPM.
# prep.py bakes the funnel mesh + cone-filtered particle list into recipe.json.
# Exercises:
#   - post_finalize.model_calls (model.set_gravity)
#   - post_finalize.mpm_attrs full-array fills (no range/indices)
#   - $mesh tag handler with inline vertices/indices

$ErrorActionPreference = "Continue"
$here     = Split-Path -Parent $MyInvocation.MyCommand.Path
$projRoot = Resolve-Path (Join-Path $here "..\..\..")
$py       = Join-Path $projRoot ".venv\Scripts\python.exe"
$viz      = Join-Path $here "..\_shared\visualize.py"

$outDir = Join-Path $here "outputs"
New-Item -ItemType Directory -Force -Path $outDir | Out-Null

$recipe   = Join-Path $here   "recipe.json"
$modelOut = Join-Path $outDir "model.json"
$stateOut = Join-Path $outDir "final.npz"
$logFile  = Join-Path $outDir "run.log"
$summary  = Join-Path $outDir "summary.txt"
$snapshot = Join-Path $outDir "snapshot.png"

"=== mpm_viscous via newton-cli ===" | Tee-Object -FilePath $logFile

"`n--- prep (regenerate recipe) ---" | Tee-Object -FilePath $logFile -Append
& $py (Join-Path $here "prep.py") 2>&1 | Tee-Object -FilePath $logFile -Append
if ($LASTEXITCODE -ne 0) { throw "prep failed" }

"`n--- model build (cuda:0) ---" | Tee-Object -FilePath $logFile -Append
& $py -m newton_cli model build --recipe $recipe --out $modelOut --device cuda:0 --json 2>&1 |
    Tee-Object -FilePath $logFile -Append
if ($LASTEXITCODE -ne 0) { throw "model build failed" }

"`n--- sim run (60 frames @ 240 fps, 1 substep, MPM, cuda:0) ---" |
    Tee-Object -FilePath $logFile -Append
& $py -m newton_cli sim run `
    --model $modelOut --solver SolverImplicitMPM `
    --solver-arg voxel_size=0.01 `
    --num-frames 60 --fps 240 --substeps 1 --device cuda:0 `
    --out $stateOut --json 2>&1 | Tee-Object -FilePath $logFile -Append
if ($LASTEXITCODE -ne 0) { throw "sim run failed" }

"`n--- visualize ---" | Tee-Object -FilePath $logFile -Append
& $py $viz $stateOut $snapshot $summary --title "mpm_viscous (CLI)" 2>&1 |
    Tee-Object -FilePath $logFile -Append

"`n--- viewer render (headless OpenGL) ---" |
    Tee-Object -FilePath $logFile -Append
& $py -m newton_cli viewer render `
    --model $modelOut --state $stateOut `
    --out (Join-Path $outDir "render.png") `
    --width 1280 --height 720 --device cuda:0 --json 2>&1 |
    Tee-Object -FilePath $logFile -Append
if ($LASTEXITCODE -ne 0) { throw "viewer render failed" }

Write-Host "`nDone. Outputs:"
Get-ChildItem $outDir | Format-Table Name, Length, LastWriteTime -AutoSize
