# cable_pile — 40 wavy rods (4 layers × 10 lanes) settling on a ground plane.
# prep.py bakes the per-cable points/quaternions into recipe.json.
# Exercises:
#   - set_builder_attr (rigid_gap)
#   - color (VBD coloring) via method dispatch
#   - 40 add_rod calls with baked positions/quaternions

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

"=== cable_pile via newton-cli ===" | Tee-Object -FilePath $logFile

"`n--- prep ---" | Tee-Object -FilePath $logFile -Append
& $py (Join-Path $here "prep.py") 2>&1 | Tee-Object -FilePath $logFile -Append
if ($LASTEXITCODE -ne 0) { throw "prep failed" }

"`n--- model build ---" | Tee-Object -FilePath $logFile -Append
& $py -m newton_cli model build --recipe $recipe --out $modelOut --device cuda:0 --json 2>&1 |
    Tee-Object -FilePath $logFile -Append
if ($LASTEXITCODE -ne 0) { throw "model build failed" }

"`n--- sim run (60 frames @ 60 fps, 10 substeps, VBD) ---" |
    Tee-Object -FilePath $logFile -Append
& $py -m newton_cli sim run `
    --model $modelOut --solver SolverVBD `
    --solver-arg iterations=5 `
    --solver-arg friction_epsilon=0.1 `
    --num-frames 60 --fps 60 --substeps 10 --device cuda:0 `
    --out $stateOut --json 2>&1 | Tee-Object -FilePath $logFile -Append
if ($LASTEXITCODE -ne 0) { throw "sim run failed" }

"`n--- visualize ---" | Tee-Object -FilePath $logFile -Append
& $py $viz $stateOut $snapshot $summary --title "cable_pile (CLI)" 2>&1 |
    Tee-Object -FilePath $logFile -Append

"`n--- viewer render ---" | Tee-Object -FilePath $logFile -Append
& $py -m newton_cli viewer render `
    --model $modelOut --state $stateOut `
    --out (Join-Path $outDir "render.png") `
    --width 1280 --height 720 --device cuda:0 --json 2>&1 |
    Tee-Object -FilePath $logFile -Append
if ($LASTEXITCODE -ne 0) { throw "viewer render failed" }

Write-Host "`nDone. Outputs:"
Get-ChildItem $outDir | Format-Table Name, Length, LastWriteTime -AutoSize
