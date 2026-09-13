from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
import tempfile
from PIL import Image, ImageChops, ImageStat
from pypdf import PdfReader
from .models import LETTER
from . import ghostscript

@dataclass
class Verification:
    ok: bool; failures: list[str] = field(default_factory=list); notes: list[str] = field(default_factory=list)

def _white_fraction(path: Path) -> float:
    with Image.open(path) as im:
        im = im.convert("L"); hist=im.histogram(); return hist[255] / (im.width*im.height)

def verify(source: Path, destination: Path) -> Verification:
    failures=[]; notes=[]
    try: src=PdfReader(str(source), strict=False); dst=PdfReader(str(destination), strict=False)
    except Exception as e: return Verification(False,[f"Cannot inspect output: {e}"])
    if len(src.pages)!=len(dst.pages): failures.append("Page count changed.")
    for i,page in enumerate(dst.pages,1):
        if abs(float(page.mediabox.width)-LETTER[0])>.01 or abs(float(page.mediabox.height)-LETTER[1])>.01: failures.append(f"Output page {i} is not US Letter.")
        if int(page.get("/Rotate",0))%360: failures.append(f"Output page {i} has nonzero rotation.")
    # Text is a broad loss detector: source pages that contain text must retain most normalized text.
    for i,(a,b) in enumerate(zip(src.pages,dst.pages),1):
        at=(a.extract_text() or "").strip(); bt=(b.extract_text() or "").strip()
        if at and len(bt) < max(3, len(at)*0.45): failures.append(f"Output page {i} lost most extractable text.")
    try:
        ghostscript.validate(destination)
        with tempfile.TemporaryDirectory(prefix="printhelper-render-") as tmp_s:
            tmp=Path(tmp_s); ghostscript.render(source,tmp/"src-%03d.png"); ghostscript.render(destination,tmp/"dst-%03d.png")
            s=sorted(tmp.glob("src-*.png")); d=sorted(tmp.glob("dst-*.png"))
            if len(d)!=len(src.pages): failures.append("Ghostscript did not render every output page.")
            for i,(sp,dp) in enumerate(zip(s,d),1):
                # Destination can be whiter because of margins. Flag only source-visible to destination-nearly-white loss.
                if _white_fraction(sp)<.995 and _white_fraction(dp)>.9999: failures.append(f"Output page {i} rendered unexpectedly blank.")
    except ghostscript.GhostscriptError as e: failures.append(f"Ghostscript output validation failed: {e}")
    return Verification(not failures, failures, notes)
