param(
  [string]$ExcelPath = ".\test.xlsx"
)
cd $PSScriptRoot\..
python -m venv .venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements_mongo.txt

if (-not (Test-Path ".env")) {
  Copy-Item ".env.example" ".env"
  Write-Host ">> Created .env – fill in MONGODB_URI then run scripts\seed.ps1"
} else {
  Write-Host ">> .env already exists."
}
