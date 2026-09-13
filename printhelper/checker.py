from __future__ import annotations
from pathlib import Path
from pypdf import PdfReader
from pypdf.generic import DictionaryObject, IndirectObject
from .models import PageInfo, Report, LETTER
from . import ghostscript
import tempfile

def _obj(v):
    return v.get_object() if isinstance(v, IndirectObject) else v

def _walk_resources(resources, counts):
    resources = _obj(resources)
    if not isinstance(resources, DictionaryObject): return
    fonts = _obj(resources.get("/Font", {}))
    if isinstance(fonts, DictionaryObject):
        for font in fonts.values():
            f = _obj(font); desc = _obj(f.get("/FontDescriptor")) if isinstance(f, DictionaryObject) else None
            if isinstance(desc, DictionaryObject) and any(k in desc for k in ("/FontFile", "/FontFile2", "/FontFile3")): counts["embedded"] += 1
            else: counts["unembedded"] += 1
    xobjs = _obj(resources.get("/XObject", {}))
    if isinstance(xobjs, DictionaryObject):
        for x in xobjs.values():
            x = _obj(x)
            if isinstance(x, DictionaryObject) and x.get("/Subtype") == "/Form":
                counts["forms"] += 1; _walk_resources(x.get("/Resources", {}), counts)

def inspect(path: str | Path, run_gs: bool = True) -> Report:
    path = Path(path)
    if not path.is_file(): raise FileNotFoundError(f"Input PDF not found or is not a file: {path}")
    if path.suffix.lower() != ".pdf": raise ValueError("Input must have a .pdf extension.")
    try: reader = PdfReader(str(path), strict=False)
    except Exception as e: raise ValueError(f"Cannot read PDF: {e}") from e
    report = Report(path=path, pdf_version=getattr(reader, "pdf_header", None))
    if reader.is_encrypted:
        report.problems.append("PDF is encrypted/password-protected."); return report
    root = reader.trailer.get("/Root", {})
    if "/AcroForm" in root: report.warnings.append("Interactive AcroForm fields are present.")
    if "/OpenAction" in root or "/AA" in root: report.warnings.append("Document actions/possible JavaScript are present.")
    counts = {"forms": 0, "embedded": 0, "unembedded": 0}
    sizes = set()
    for i, page in enumerate(reader.pages, 1):
        box = page.mediabox; w, h = float(box.width), float(box.height); rot = int(page.get("/Rotate", 0)) % 360
        crop = page.get("/CropBox"); cb = tuple(map(float, crop)) if crop else None
        text = (page.extract_text() or "").strip()
        report.pages.append(PageInfo(i,w,h,rot,tuple(map(float,box)),cb,not bool(text)))
        sizes.add((round(w,2),round(h,2))); _walk_resources(page.get("/Resources", {}), counts)
        if rot: report.warnings.append(f"Page {i} has rotation {rot} deg.")
        if not (w <= LETTER[0]+.01 and h <= LETTER[1]+.01): report.problems.append(f"Page {i} is {w:.1f} x {h:.1f} pt and cannot fit Letter at 100% scale.")
    report.form_xobjects, report.embedded_fonts, report.unembedded_fonts = counts["forms"], counts["embedded"], counts["unembedded"]
    if len(sizes) > 1: report.warnings.append("Pages have inconsistent dimensions.")
    if any(not p.is_letter for p in report.pages): report.warnings.append("Non-Letter page size(s) detected; normalization is recommended.")
    if counts["forms"]: report.warnings.append(f"{counts['forms']} Form XObject(s) found; whole-page forms can be printer-sensitive.")
    if counts["unembedded"]: report.warnings.append(f"{counts['unembedded']} font resource(s) may not be embedded.")
    if run_gs:
        try:
            ghostscript.validate(path); report.gs_parse_ok = True
            with tempfile.TemporaryDirectory(prefix="printhelper-") as tmp:
                ghostscript.render(path, Path(tmp) / "source-%03d.png"); report.gs_render_ok = len(list(Path(tmp).glob("source-*.png"))) == len(report.pages)
                if not report.gs_render_ok: report.problems.append("Ghostscript did not render every page.")
        except ghostscript.GhostscriptError as e: report.gs_parse_ok = report.gs_render_ok = False; report.warnings.append(str(e))
    return report

def report_dict(r: Report):
    return {"file": str(r.path), "pdf_version": r.pdf_version, "pages": len(r.pages), "status": r.status, "warnings": r.warnings, "problems": r.problems, "ghostscript_parse": r.gs_parse_ok, "ghostscript_render": r.gs_render_ok, "form_xobjects": r.form_xobjects, "fonts": {"embedded":r.embedded_fonts,"possibly_unembedded":r.unembedded_fonts}}

def format_report(r: Report) -> str:
    out=["PrintHelper", "-"*35, f"File: {r.path.name}", f"Pages: {len(r.pages)}", f"PDF version: {r.pdf_version or 'unknown'}", "", "Page geometry:"]
    for p in r.pages: out.append(f"  Page {p.number}: {p.width/72:.2f} x {p.height/72:.2f} in, rotation {p.rotation} deg")
    out += ["", "Compatibility:"]
    out += ["  [OK] Ghostscript parses successfully" if r.gs_parse_ok else "  [WARN] Ghostscript validation unavailable or failed"]
    out += ["  [OK] All pages render" if r.gs_render_ok else "  [WARN] Rendering check unavailable or failed"]
    out += [f"  [WARN] {x}" for x in r.warnings] + [f"  [FAIL] {x}" for x in r.problems]
    out += ["", f"Overall: {r.status}"]
    return "\n".join(out)
