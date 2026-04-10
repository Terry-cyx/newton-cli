# nut_bolt_sdf — single nut+bolt assembly with hydroelastic SDF contacts.
# prep.py downloads the IsaacGymEnvs nut/bolt OBJs (cached after first run),
# recenters them, and bakes vertices/indices into recipe.json.
# build_sdf runs at recipe-execution time inside the $mesh tag handler.

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

"=== nut_bolt_sdf via newton-cli ===" | Tee-Object -FilePath $logFile

"`n--- prep ---" | Tee-Object -FilePath $logFile -Append
& $py (Join-Path $here "prep.py") 2>&1 | Tee-Object -FilePath $logFile -Append
if ($LASTEXITCODE -ne 0) { throw "prep failed" }

"`n--- model build (slow: builds SDFs) ---" | Tee-Object -FilePath $logFile -Append
& $py -m newton_cli model build --recipe $recipe --out $modelOut --device cuda:0 --json 2>&1 |
    Tee-Object -FilePath $logFile -Append
if ($LASTEXITCODE -ne 0) { throw "model build failed" }

"`n--- sim run (60 frames @ 120 fps, 5 substeps, MuJoCo) ---" |
    Tee-Object -FilePath $logFile -Append
& $py -m newton_cli sim run `
    --model $modelOut --solver SolverMuJoCo `
    --solver-arg use_mujoco_contacts=false `
    --solver-arg solver=newton `
    --solver-arg integrator=implicitfast `
    --solver-arg cone=elliptic `
    --solver-arg iterations=15 `
    --solver-arg ls_iterations=100 `
    --solver-arg impratio=1.0 `
    --num-frames 60 --fps 120 --substeps 5 --device cuda:0 `
    --out $stateOut --json 2>&1 | Tee-Object -FilePath $logFile -Append
if ($LASTEXITCODE -ne 0) { throw "sim run failed" }

"`n--- visualize ---" | Tee-Object -FilePath $logFile -Append
& $py $viz $stateOut $snapshot $summary --title "nut_bolt_sdf (CLI)" 2>&1 |
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
