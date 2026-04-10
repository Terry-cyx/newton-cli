# cloth_poker_cards — 52 cards drop onto a cube platform (VBD).
# Skipping the upstream example's kinematic sphere knocking animation.

$ErrorActionPreference = "Continue"
$here     = Split-Path -Parent $MyInvocation.MyCommand.Path
$projRoot = Resolve-Path (Join-Path $here "..\..\..")
$py       = Join-Path $projRoot ".venv\Scripts\python.exe"
$viz      = Join-Path $here "..\_shared\visualize.py"

$outDir = Join-Path $here "outputs"
New-Item -ItemType Directory -Force -Path $outDir | Out-Null

$prep     = Join-Path $here   "prep.py"
$recipe   = Join-Path $here   "recipe.json"
$modelOut = Join-Path $outDir "model.json"
$stateOut = Join-Path $outDir "final.npz"
$logFile  = Join-Path $outDir "run.log"
$summary  = Join-Path $outDir "summary.txt"
$snapshot = Join-Path $outDir "snapshot.png"

"=== cloth_poker_cards via newton-cli ===" | Tee-Object -FilePath $logFile
"--- prep ---" | Tee-Object -FilePath $logFile -Append
& $py $prep 2>&1 | Tee-Object -FilePath $logFile -Append
if ($LASTEXITCODE -ne 0) { throw "prep failed" }

"`n--- model build (cuda:0) ---" | Tee-Object -FilePath $logFile -Append
& $py -m newton_cli model build --recipe $recipe --out $modelOut --device cuda:0 --json 2>&1 |
    Tee-Object -FilePath $logFile -Append
if ($LASTEXITCODE -ne 0) { throw "model build failed" }

"`n--- sim run (60 frames @ 60 fps, 20 substeps, VBD iter=10, cuda:0) ---" |
    Tee-Object -FilePath $logFile -Append
& $py -m newton_cli sim run `
    --model $modelOut --solver SolverVBD `
    --solver-arg iterations=10 `
    --solver-arg particle_enable_self_contact=true `
    --solver-arg particle_self_contact_radius=0.001 `
    --solver-arg particle_self_contact_margin=0.0015 `
    --num-frames 60 --fps 60 --substeps 20 --device cuda:0 `
    --out $stateOut --json 2>&1 | Tee-Object -FilePath $logFile -Append
if ($LASTEXITCODE -ne 0) { throw "sim run failed" }

"`n--- visualize ---" | Tee-Object -FilePath $logFile -Append
& $py $viz $stateOut $snapshot $summary --title "cloth_poker_cards (CLI)" 2>&1 |
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
