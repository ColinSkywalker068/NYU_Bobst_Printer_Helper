from pathlib import Path
import pytest
from pypdf import PdfWriter
from printhelper.checker import inspect
from printhelper.transformer import default_output, transform, TransformError, SIZE_MAX
from printhelper.ghostscript import executable

def make_pdf(path, pages):
    w=PdfWriter()
    for width,height,rotation in pages:
        p=w.add_blank_page(width,height)
        if rotation: p.rotate(rotation)
    with path.open("wb") as f: w.write(f)
    return path

def test_letter_pdf(tmp_path):
    r=inspect(make_pdf(tmp_path/'letter.pdf',[(612,792,0)]),run_gs=False)
    assert r.status == 'PASS'

def test_small_and_mixed_pages(tmp_path):
    r=inspect(make_pdf(tmp_path/'mixed.pdf',[(432,648,0),(612,792,0)]),run_gs=False)
    assert 'NEEDS NORMALIZATION' == r.status
    assert any('inconsistent' in x for x in r.warnings)

def test_rotation(tmp_path):
    r=inspect(make_pdf(tmp_path/'rotated.pdf',[(612,792,90)]),run_gs=False)
    assert r.pages[0].rotation == 90

def test_blank_page(tmp_path):
    r=inspect(make_pdf(tmp_path/'blank.pdf',[(432,648,0)]),run_gs=False)
    assert r.pages[0].is_blank_text

def test_larger_rejected(tmp_path):
    p=make_pdf(tmp_path/'big.pdf',[(700,800,0)])
    r=inspect(p,run_gs=False); assert r.status.startswith('UNSAFE')
    with pytest.raises(TransformError): transform(p)

def test_collision_filename(tmp_path):
    source=tmp_path/'file with spaces.pdf'; source.touch()
    (tmp_path/'file with spaces_bobst_safe.pdf').touch()
    assert default_output(source,tmp_path).name == 'file with spaces_bobst_safe_2.pdf'

def test_missing_file():
    with pytest.raises(FileNotFoundError): inspect('does-not-exist.pdf',run_gs=False)

def test_invalid_pdf(tmp_path):
    p=tmp_path/'bad.pdf'; p.write_text('not a pdf')
    with pytest.raises(ValueError): inspect(p,run_gs=False)

@pytest.mark.skipif(executable() is None, reason='Ghostscript unavailable: transformation test skipped')
def test_transform_and_verify(tmp_path):
    p=make_pdf(tmp_path/'small.pdf',[(432,648,0)])
    out=transform(p)
    r=inspect(out,run_gs=True)
    assert r.status == 'PASS' and out.exists()

@pytest.mark.skipif(executable() is None, reason='Ghostscript unavailable: transformation test skipped')
def test_size_max_transform(tmp_path):
    p=make_pdf(tmp_path/'small max.pdf',[(432,648,0)])
    out=transform(p, output=tmp_path/'max.pdf', size_mode=SIZE_MAX)
    r=inspect(out,run_gs=True)
    assert r.status == 'PASS' and r.pages[0].is_letter