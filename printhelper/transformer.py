from __future__ import annotations
import os, shutil, tempfile
from pathlib import Path
from .models import LETTER
from .checker import inspect
from . import ghostscript
from .validator import verify

SIZE_ORIGINAL = "size_original"
SIZE_MAX = "size_max"

class TransformError(RuntimeError): pass

def default_output(source: Path, directory: Path, overwrite: bool = False) -> Path:
    base = directory / f"{source.stem}_bobst_safe.pdf"
    if overwrite or not base.exists(): return base
    n = 2
    while (candidate := directory / f"{source.stem}_bobst_safe_{n}.pdf").exists(): n += 1
    return candidate

def transform(source: str | Path, output: str | Path | None = None, output_dir: str | Path | None = None, overwrite: bool = False, force_normalize: bool = False, size_mode: str = SIZE_ORIGINAL) -> Path:
    if size_mode not in {SIZE_ORIGINAL, SIZE_MAX}:
        raise TransformError(f"Unknown size mode: {size_mode}")
    source = Path(source).resolve(); report = inspect(source, run_gs=False)
    too_large = [p for p in report.pages if not p.fits_letter_at_100]
    if too_large and size_mode == SIZE_ORIGINAL and not force_normalize:
        raise TransformError("Refusing conversion: " + "; ".join(report.problems) + ". Use --size-mode size_max to fit proportionally, or --force-normalize only if you accept clipping.")
    if output is not None: final = Path(output).expanduser().resolve()
    else:
        directory = Path(output_dir).expanduser().resolve() if output_dir else source.parent
        final = default_output(source, directory, overwrite)
    if final == source: raise TransformError("Output path must not be the source PDF.")
    if final.exists() and not overwrite: raise TransformError(f"Output already exists: {final}. Choose another name or use --overwrite.")
    final.parent.mkdir(parents=True, exist_ok=True)
    if not os.access(final.parent, os.W_OK): raise TransformError(f"Output directory is not writable: {final.parent}")
    ghostscript.require()
    with tempfile.TemporaryDirectory(prefix="printhelper-") as tmp_s:
        tmp = Path(tmp_s); page_files=[]
        for page in report.pages:
            one = tmp / f"page-{page.number:05d}.pdf"
            common = ["-sDEVICE=pdfwrite", "-dCompatibilityLevel=1.4", "-dFIXEDMEDIA", "-dDEVICEWIDTHPOINTS=612", "-dDEVICEHEIGHTPOINTS=792", "-dAutoRotatePages=/None", "-dPreserveAnnots=false", "-dFirstPage="+str(page.number), "-dLastPage="+str(page.number), f"-sOutputFile={one}"]
            if size_mode == SIZE_ORIGINAL:
                x, y = (LETTER[0]-page.width)/2, (LETTER[1]-page.height)/2
                setpage = f"<</PageSize [612 792] /PageOffset [{x:.6f} {y:.6f}]>> setpagedevice"
                command = [*common, "-c", setpage, "-f", str(source)]
            else:
                # Ghostscript calculates one uniform fit factor and centers it; proportions remain unchanged.
                command = [*common, "-dPDFFitPage", str(source)]
            ghostscript.run(command)
            page_files.append(one)
        staged = tmp / "normalized.pdf"
        ghostscript.run(["-sDEVICE=pdfwrite", "-dCompatibilityLevel=1.4", "-dFIXEDMEDIA", "-dAutoRotatePages=/None", "-dPreserveAnnots=false", "-dDEVICEWIDTHPOINTS=612", "-dDEVICEHEIGHTPOINTS=792", f"-sOutputFile={staged}", *map(str,page_files)])
        result = verify(source, staged)
        if not result.ok: raise TransformError("Verification failed; no output was saved:\n" + "\n".join(result.failures))
        shutil.move(str(staged), str(final))
    return final