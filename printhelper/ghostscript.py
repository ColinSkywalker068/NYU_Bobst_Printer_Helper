from __future__ import annotations
import shutil, subprocess
from pathlib import Path

class GhostscriptError(RuntimeError): pass

def executable() -> str | None:
    for name in ("gswin64c.exe", "gswin32c.exe", "gs"):
        found = shutil.which(name)
        if found: return found
    program_files = Path(r"C:\Program Files\gs")
    if program_files.is_dir():
        candidates = sorted(program_files.glob("*/bin/gswin64c.exe"), reverse=True)
        if candidates:
            return str(candidates[0])
    return None

def require() -> str:
    found = executable()
    if not found:
        raise GhostscriptError("Ghostscript is required. Install it, then ensure gs (macOS/Linux) or gswin64c.exe (Windows) is on PATH.")
    return found

def run(args: list[str], timeout: int = 180) -> subprocess.CompletedProcess[str]:
    command = [require(), "-dSAFER", "-dBATCH", "-dNOPAUSE", "-dNOPROMPT", *args]
    try:
        result = subprocess.run(command, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout)
    except subprocess.TimeoutExpired as e:
        raise GhostscriptError(f"Ghostscript timed out after {timeout}s.") from e
    if result.returncode:
        detail = (result.stderr or result.stdout).strip()[-3000:]
        raise GhostscriptError(f"Ghostscript failed (exit {result.returncode}):\n{detail}")
    return result

def validate(pdf: Path) -> None:
    run(["-sDEVICE=nullpage", str(pdf)])

def render(pdf: Path, output_pattern: Path, dpi: int = 72) -> None:
    run(["-sDEVICE=pnggray", f"-r{dpi}", f"-sOutputFile={output_pattern}", str(pdf)])
