param(
  [string]$ExcelPath = ".\test.xlsx"
)
cd $PSScriptRoot\..
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
if (-not (Test-Path $ExcelPath)) {
  Write-Error "Could not find $ExcelPath. Pass a path: scripts\seed.ps1 -ExcelPath C:\full\path.xlsx"
  exit 1
}
python -m etl.load_recipes_mongo $ExcelPath
