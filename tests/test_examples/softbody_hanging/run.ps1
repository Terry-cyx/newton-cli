# softbody_hanging — 4 tet-grid soft bodies hanging from fixed left edges (cuda:0).

$ErrorActionPreference = "Stop"
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

"=== softbody_hanging via newton-cli ===" | Tee-Object -FilePath $logFile

"--- model build (cuda:0) ---" | Tee-Object -FilePath $logFile -Append
& $py -m newton_cli model build --recipe $recipe --out $modelOut --device cuda:0 --json 2>&1 |
    Tee-Object -FilePath $logFile -Append
if ($LASTEXITCODE -ne 0) { throw "model build failed (exit $LASTEXITCODE)" }

"`n--- sim run (100 frames @ 60 fps, 10 substeps, VBD iter=10, cuda:0) ---" |
    Tee-Object -FilePath $logFile -Append
& $py -m newton_cli sim run `
    --model      $modelOut `
    --solver     SolverVBD `
    --solver-arg iterations=10 `
    --solver-arg particle_enable_self_contact=false `
    --solver-arg particle_enable_tile_solve=false `
    --num-frames 100 `
    --fps        60 `
    --substeps   10 `
    --device     cuda:0 `
    --out        $stateOut `
    --json 2>&1 | Tee-Object -FilePath $logFile -Append
if ($LASTEXITCODE -ne 0) { throw "sim run failed (exit $LASTEXITCODE)" }

"`n--- visualize ---" | Tee-Object -FilePath $logFile -Append
& $py $viz $stateOut $snapshot $summary --title "softbody_hanging (CLI)" 2>&1 |
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
