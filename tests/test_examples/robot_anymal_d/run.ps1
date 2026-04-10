# robot_anymal_d — 2 ANYbotics ANYmal D quadrupeds from remote USD asset.
# Requires newton[sim] + GitPython. First run downloads the asset from GitHub.

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

"=== robot_anymal_d via newton-cli ===" | Tee-Object -FilePath $logFile

"--- prep (may download asset from GitHub on first run) ---" |
    Tee-Object -FilePath $logFile -Append
& $py $prep 2>&1 | Tee-Object -FilePath $logFile -Append
if ($LASTEXITCODE -ne 0) { throw "prep failed (exit $LASTEXITCODE)" }

"`n--- model build (cuda:0) ---" | Tee-Object -FilePath $logFile -Append
& $py -m newton_cli model build --recipe $recipe --out $modelOut --device cuda:0 --json 2>&1 |
    Tee-Object -FilePath $logFile -Append
if ($LASTEXITCODE -ne 0) { throw "model build failed (exit $LASTEXITCODE)" }

"`n--- sim run (50 frames @ 50 fps, 4 substeps, MuJoCo, cuda:0) ---" |
    Tee-Object -FilePath $logFile -Append
& $py -m newton_cli sim run `
    --model      $modelOut `
    --solver     SolverMuJoCo `
    --num-frames 50 `
    --fps        50 `
    --substeps   4 `
    --device     cuda:0 `
    --out        $stateOut `
    --json 2>&1 | Tee-Object -FilePath $logFile -Append
if ($LASTEXITCODE -ne 0) { throw "sim run failed (exit $LASTEXITCODE)" }

"`n--- visualize ---" | Tee-Object -FilePath $logFile -Append
& $py $viz $stateOut $snapshot $summary --title "robot_anymal_d (CLI)" 2>&1 |
    Tee-Object -FilePath $logFile -Append

"`n--- viewer render (headless OpenGL) ---" |
    Tee-Object -FilePath $logFile -Append
& $py -m newton_cli viewer render `
    --model  $modelOut `
    --state  $stateOut `
    --out    (Join-Path $outDir "render.png") `
    --width  1280 `
    --height 720 `
    --device cuda:0 `
    --json 2>&1 | Tee-Object -FilePath $logFile -Append
if ($LASTEXITCODE -ne 0) { throw "viewer render failed (exit $LASTEXITCODE)" }

Write-Host "`nDone. Outputs:"
Get-ChildItem $outDir | Format-Table Name, Length, LastWriteTime -AutoSize
