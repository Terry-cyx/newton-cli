# pyramid — stack of 6 cubes in a 3-row pyramid, must not topple under gravity.

$ErrorActionPreference = "Stop"
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

"=== pyramid via newton-cli ===" | Tee-Object -FilePath $logFile
"--- prep ---" | Tee-Object -FilePath $logFile -Append
& $py $prep 2>&1 | Tee-Object -FilePath $logFile -Append
if ($LASTEXITCODE -ne 0) { throw "prep failed" }

"`n--- model build ---" | Tee-Object -FilePath $logFile -Append
& $py -m newton_cli model build --recipe $recipe --out $modelOut --json 2>&1 |
    Tee-Object -FilePath $logFile -Append
if ($LASTEXITCODE -ne 0) { throw "model build failed" }

"`n--- sim run (100 frames @ 100 fps, XPBD iter=2, contact_relax=0.8, cpu) ---" |
    Tee-Object -FilePath $logFile -Append
& $py -m newton_cli sim run `
    --model $modelOut --solver SolverXPBD `
    --solver-arg iterations=2 `
    --solver-arg rigid_contact_relaxation=0.8 `
    --num-frames 100 --fps 100 --substeps 10 --device cpu `
    --out $stateOut --json 2>&1 | Tee-Object -FilePath $logFile -Append
if ($LASTEXITCODE -ne 0) { throw "sim run failed" }

"`n--- visualize ---" | Tee-Object -FilePath $logFile -Append
& $py $viz $stateOut $snapshot $summary --title "pyramid (CLI)" 2>&1 |
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
