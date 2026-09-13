# PrintHelper

PrintHelper is a local command-line utility for preparing PDFs for dependable printing. It checks a PDF for structural and rendering risks, then can rewrite it as a normal US Letter PDF using Ghostscript. It never alters the source file.

Some PDFs display normally but fail in printer RIP pipelines. One known issue is a page that simply invokes an imported whole-page Form XObject (for example, `/fzFrm0 Do`). PrintHelper has Ghostscript re-interpret and rewrite each page rather than using page embedding, so the final output has direct printable page content. It validates the output before putting it in your chosen folder.

PrintHelper is a compatibility heuristic—not a guarantee of any physical printer's behavior. Duplex long-edge versus short-edge is configured in the print dialog, not by PDF normalization.

## Requirements

- Python 3.10 or newer
- Ghostscript
- A local copy of this repository/project folder

Install Ghostscript before transforming files:

- Windows: install the 64-bit AGPL release from [Ghostscript](https://ghostscript.com/releases/gsdnld.html).
- macOS: `brew install ghostscript`
- Ubuntu/Debian/WSL: `sudo apt install ghostscript`

PrintHelper detects `gs` on macOS/Linux and `gswin64c.exe` or `gswin32c.exe` on Windows. It also checks the conventional Windows Ghostscript installation location.

## Setup

Create a project-local virtual environment and install the pinned dependencies:

### Windows PowerShell

```powershell
cd path\to\PrintHelper
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pip install -e .
```

### macOS, Linux, or WSL

```sh
cd /path/to/PrintHelper
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m pip install -e .
```

The supplied launchers use the project-local `.venv` interpreter automatically, so manual activation is optional. For interactive development, activate it with one of these commands:

```powershell
.\.venv\Scripts\Activate.ps1
```

```sh
. .venv/bin/activate
```

## Usage

### Check only

Analyzes a PDF and does not create or modify any files.

```powershell
.\scripts\check.ps1 "C:\path\to\document.pdf"
```

```sh
./scripts/check.sh "/path/to/document.pdf"
```

Useful scriptable options:

```text
--json                  Emit structured inspection data.
--quiet                 Suppress the formatted report.
```

### Transform only

Creates a validated print-safe copy without an approval prompt.

```powershell
.\scripts\transform.ps1 "C:\path\to\document.pdf"
.\scripts\transform.ps1 "C:\path\to\document.pdf" --size-mode size_max
.\scripts\transform.ps1 "C:\path\to\document.pdf" --output-dir "C:\Print Output"
.\scripts\transform.ps1 "C:\path\to\document.pdf" --output "C:\Print Output\ready.pdf"
```

### Full interactive workflow

Checks first, asks whether to edit, prompts for a sizing mode, then prompts for an output directory:

```powershell
.\scripts\run-full.ps1 "C:\path\to\document.pdf"
```

Scriptable non-interactive use:

```powershell
.\scripts\run-full.ps1 "C:\path\to\document.pdf" --yes --size-mode size_original --quiet
```

## Sizing modes

| Mode | Behavior | Best for |
| --- | --- | --- |
| `size_original` (default) | Keeps the source page at exactly 100% physical scale, centered on an 8.5 × 11 in Letter page. | PDFs already sized for print, such as 6 × 9 in pages where physical scale must not change. |
| `size_max` | Applies one uniform scale factor to fit the largest possible area on Letter. It preserves aspect ratio but may enlarge smaller pages or shrink larger ones. | Readability or maximum Letter-page use is more important than preserving the source's original physical size. |

`size_original` refuses pages larger than Letter unless `--force-normalize` is explicitly selected; that override can clip content. `size_max` is explicit permission to proportionally fit oversized pages.

## CLI reference

All three entry points accept an input PDF path:

```text
python check_pdf.py INPUT.pdf [--json] [--quiet]
python transform_pdf.py INPUT.pdf [OPTIONS]
python run_full.py INPUT.pdf [OPTIONS]
```

Transform and full-workflow options:

```text
--size-mode {size_original,size_max}
--output-dir PATH
--output FILE
--overwrite
--force-normalize
--yes
--quiet
--json
```

Output defaults to `ORIGINAL_bobst_safe.pdf` beside the source. Existing names become `_2`, `_3`, and so on. The source is never overwritten.

## Launcher formats and skeletons

The `scripts/` directory contains launchers that forward all arguments to the appropriate Python entry point and use the local virtual environment.

### PowerShell (`scripts/check.ps1`)

```powershell
param([Parameter(ValueFromRemainingArguments=$true)][string[]]$Args)
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$python = Join-Path $root '.venv\Scripts\python.exe'
& $python (Join-Path $root 'check_pdf.py') @Args
exit $LASTEXITCODE
```

`transform.ps1` and `run-full.ps1` use the same pattern, replacing `check_pdf.py` with `transform_pdf.py` or `run_full.py`.

### Windows batch (`scripts/check.bat`)

```bat
@echo off
"%~dp0..\.venv\Scripts\python.exe" "%~dp0..\check_pdf.py" %*
```

### POSIX shell (`scripts/check.sh`)

```sh
#!/usr/bin/env sh
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
exec "$root/.venv/bin/python" "$root/check_pdf.py" "$@"
```

The shell `transform.sh` and `run-full.sh` have the same shape and point to their matching entry points.

## Project structure

```text
PrintHelper/
├── .venv/                    # local Python environment; do not commit
├── printhelper/
│   ├── checker.py             # PDF structural and compatibility inspection
│   ├── cli.py                 # command-line arguments and interactive prompts
│   ├── ghostscript.py         # Ghostscript detection and safe subprocess calls
│   ├── models.py              # report and page data structures
│   ├── transformer.py         # size modes and Ghostscript rewrite pipeline
│   ├── validator.py           # post-transform geometry, text, render checks
│   └── __init__.py
├── scripts/                   # PowerShell, batch, and shell launchers
├── tests/                     # synthetic PDF tests
├── check_pdf.py               # check-only entry point
├── transform_pdf.py           # transform-only entry point
├── run_full.py                # interactive entry point
├── pyproject.toml             # package metadata and runtime dependencies
└── requirements.txt           # pinned runtime, test, and transitive dependencies
```

## Verification and safety

The process writes to a temporary location, validates the output, then moves it to the requested destination. Validation checks matching page count, Letter geometry, zero rotation, broad text retention, Ghostscript parse/render success, embedded font information, and unexpected blank output.

## Dependencies

`requirements.txt` pins the runtime, test, and secondary/transitive packages used for the tested environment. `pyproject.toml` lists the smaller runtime dependency set. Ghostscript is an external system dependency, not a pip package.

## Limitations

Password-protected PDFs need an unprotected copy. Very unusual PDF constructs, unavailable fonts, malformed files, transparency, and printer-specific job settings can still affect a physical print. PrintHelper reports detected risk; it does not promise a printer will accept or duplex a document in a particular way.