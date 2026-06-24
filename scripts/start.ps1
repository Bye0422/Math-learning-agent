$ErrorActionPreference = "Stop"

$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$Streamlit = Join-Path $ProjectRoot ".venv\Scripts\streamlit.exe"

if (-not (Test-Path $Python)) {
    throw "Python venv not found. Create it first: py -m venv .venv"
}

if (-not (Test-Path $Streamlit)) {
    throw "Streamlit not found. Install dependencies: .\.venv\Scripts\python.exe -m pip install -r requirements.txt"
}

Push-Location $ProjectRoot
try {
    & $Python "scripts\check_env.py"
    if ($LASTEXITCODE -ne 0) {
        throw "Environment check failed."
    }

    & $Streamlit run "app.py"
}
finally {
    Pop-Location
}
