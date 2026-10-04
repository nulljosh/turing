# Samantha on Windows: one command in PowerShell.
#   irm https://raw.githubusercontent.com/nulljosh/turing/main/install/install.ps1 | iex
# Puts her in ~\samantha, builds a Python env, downloads her tool picker (a small GGUF) and starts chat.
# The parts that drive your screen and apps stay on the Mac; chat, her tool picker and the portable tools run here.
$ErrorActionPreference = "Stop"
$Dir = if ($env:SAMANTHA_DIR) { $env:SAMANTHA_DIR } else { Join-Path $HOME "samantha" }
$Gguf = "https://github.com/nulljosh/turing/releases/download/portable/samantha-hands.gguf"
if (-not (Get-Command python -ErrorAction SilentlyContinue)) { Write-Host "Samantha needs Python. Install it from python.org, then run this again."; exit 1 }
if (-not (Get-Command git -ErrorAction SilentlyContinue)) { Write-Host "Samantha needs git. Install it from git-scm.com, then run this again."; exit 1 }
if (Test-Path (Join-Path $Dir ".git")) { git -C $Dir pull -q } else { git clone -q --depth 1 https://github.com/nulljosh/turing $Dir }
Set-Location $Dir
python -m venv .venv
$Py = Join-Path $Dir ".venv\Scripts\python.exe"
& $Py -m pip install -q --upgrade pip
& $Py -m pip install -q llama-cpp-python --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cpu
New-Item -ItemType Directory -Force models | Out-Null
$Model = Join-Path $Dir "models\samantha-hands.gguf"
if (-not (Test-Path $Model)) { Invoke-WebRequest $Gguf -OutFile $Model }
Write-Host "Ready. Starting Samantha. Run it again any time: $Py app\chat.py"
& $Py app\chat.py
