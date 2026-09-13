from __future__ import annotations
import argparse, json
from pathlib import Path
from .checker import inspect, format_report, report_dict
from .transformer import transform, TransformError, SIZE_ORIGINAL, SIZE_MAX

def parser(mode: str):
    p=argparse.ArgumentParser(prog={"check":"check_pdf.py","transform":"transform_pdf.py","full":"run_full.py"}[mode], description="PrintHelper PDF compatibility utility")
    p.add_argument("pdf", help="input PDF path")
    p.add_argument("--output-dir", type=Path); p.add_argument("--output", type=Path); p.add_argument("--overwrite", action="store_true")
    p.add_argument("--size-mode", choices=[SIZE_ORIGINAL,SIZE_MAX], default=SIZE_ORIGINAL, help="size_original keeps 100%% scale; size_max uniformly fits the largest Letter area")
    p.add_argument("--force-normalize", action="store_true", help="allow larger pages to be clipped in size_original mode")
    p.add_argument("--yes", action="store_true", help="approve transform in full workflow")
    p.add_argument("--quiet", action="store_true"); p.add_argument("--json", action="store_true")
    return p

def _choose_size_mode(default: str) -> str:
    prompt = "Sizing mode [size_original = 100% centered; size_max = proportional max Letter] (size_original): "
    try: value=input(prompt).strip().lower()
    except EOFError: return default
    if not value: return default
    if value in {SIZE_ORIGINAL, SIZE_MAX}: return value
    print("Unknown size mode; using size_original.")
    return SIZE_ORIGINAL

def main(mode: str) -> int:
    args=parser(mode).parse_args()
    try: report=inspect(args.pdf)
    except Exception as e: print(f"Error: {e}"); return 2
    if args.json: print(json.dumps(report_dict(report), indent=2))
    elif not args.quiet: print(format_report(report))
    if mode=="check": return 0 if not report.problems else 1
    proceed = mode=="transform" or args.yes
    if mode=="full" and not proceed:
        try: proceed=input("\nCreate Bobst-safe version? [y/N]: ").strip().lower() in {"y","yes"}
        except EOFError: proceed=False
    if not proceed:
        if not args.quiet: print("No output created.")
        return 0
    if mode=="full" and not args.yes:
        args.size_mode = _choose_size_mode(args.size_mode)
    out_dir=args.output_dir
    if mode=="full" and args.output is None and out_dir is None and not args.yes:
        value=input("Save directory [press Enter to use original PDF directory]: ").strip()
        out_dir=Path(value).expanduser() if value else None
    try:
        result=transform(args.pdf,args.output,out_dir,args.overwrite,args.force_normalize,args.size_mode)
    except (TransformError, Exception) as e: print(f"Transformation failed: {e}"); return 1
    if args.json: print(json.dumps({"output":str(result),"verified":True,"size_mode":args.size_mode}))
    elif not args.quiet: print(f"\nSaved and verified ({args.size_mode}):\n  {result}")
    return 0