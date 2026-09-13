param([Parameter(ValueFromRemainingArguments=$true)][string[]]$Args)
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$python = Join-Path $root '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $python)) { Write-Error 'PrintHelper environment is missing. Run setup first.'; exit 1 }
& $python (Join-Path $root 'run_full.py') @Args
exit $LASTEXITCODE