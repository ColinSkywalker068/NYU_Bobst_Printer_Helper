from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path

LETTER = (612.0, 792.0)

@dataclass
class PageInfo:
    number: int; width: float; height: float; rotation: int
    media_box: tuple[float, float, float, float]
    crop_box: tuple[float, float, float, float] | None = None
    is_blank_text: bool = False

    @property
    def fits_letter_at_100(self): return self.width <= LETTER[0] + .01 and self.height <= LETTER[1] + .01
    @property
    def is_letter(self): return abs(self.width-LETTER[0]) < .01 and abs(self.height-LETTER[1]) < .01

@dataclass
class Report:
    path: Path; pdf_version: str | None = None; pages: list[PageInfo] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list); problems: list[str] = field(default_factory=list)
    facts: list[str] = field(default_factory=list); gs_parse_ok: bool | None = None; gs_render_ok: bool | None = None
    form_xobjects: int = 0; embedded_fonts: int = 0; unembedded_fonts: int = 0

    @property
    def status(self):
        if self.problems: return "UNSAFE FOR 100%-SCALE LETTER CONVERSION"
        if self.warnings or not all(p.is_letter and p.rotation == 0 for p in self.pages): return "NEEDS NORMALIZATION"
        return "PASS"
