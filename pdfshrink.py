#!/usr/bin/env python3
"""pdfshrink - shrink PDFs locally using Ghostscript. No SaaS, no uploads.

Install Ghostscript once:
  macOS:    brew install ghostscript
  Ubuntu:   sudo apt install ghostscript
  Windows:  winget install ArtifexSoftware.GhostScript

Examples:
  pdfshrink.py big.pdf                      # ebook preset -> big.min.pdf
  pdfshrink.py big.pdf -p screen            # smallest, lowest quality
  pdfshrink.py *.pdf -p printer -i          # batch, overwrite in place
  pdfshrink.py scan.pdf --scan              # scanned docs: re-encode images (150 dpi, q60)
  pdfshrink.py scan.pdf --scan --gray -q 45 # smaller still
  pdfshrink.py scan.pdf --dpi 110 --gray    # custom downsampling + grayscale
"""
import argparse
import os
import shutil
import subprocess
import sys
import tempfile

PRESETS = {
    "screen": "/screen",      # ~72 dpi, smallest
    "ebook": "/ebook",        # ~150 dpi, good balance (default)
    "printer": "/printer",    # ~300 dpi
    "prepress": "/prepress",  # ~300 dpi, color preserving, largest
}


def find_gs():
    for name in ("gs", "gswin64c", "gswin32c"):
        path = shutil.which(name)
        if path:
            return path
    sys.exit("Ghostscript not found. Install it first (see top of this file).")


def jpeg_qfactor(q):
    """Map JPEG quality 1-100 to Ghostscript QFactor (lower = better quality)."""
    return round(max(0.05, (100 - q) / 50), 2)


def build_cmd(gs, src, dst, a):
    cmd = [
        gs, "-sDEVICE=pdfwrite", "-dCompatibilityLevel=1.5",
        "-dNOPAUSE", "-dBATCH", "-dQUIET", "-dSAFER",
        f"-dPDFSETTINGS={PRESETS[a.preset]}",
        "-dDetectDuplicateImages=true", "-dCompressFonts=true",
        "-dSubsetFonts=true",
    ]
    # --scan = sensible defaults for scanned documents
    dpi = a.dpi or (150 if a.scan else None)
    quality = a.quality or (60 if a.scan else None)
    recompress = a.recompress or a.scan or quality is not None

    if dpi:
        for kind in ("Color", "Gray"):
            cmd += [f"-dDownsample{kind}Images=true",
                    f"-d{kind}ImageResolution={dpi}",
                    f"-d{kind}ImageDownsampleType=/Bicubic",
                    # default threshold is 1.5x: scans at 200 dpi would be skipped
                    f"-d{kind}ImageDownsampleThreshold=1.0"]
        cmd += ["-dDownsampleMonoImages=true",
                f"-dMonoImageResolution={max(dpi * 2, 300)}"]
    if recompress:
        # existing JPEGs are passed through untouched by default; force re-encode
        cmd += ["-dPassThroughJPEGImages=false",
                "-dAutoFilterColorImages=false", "-dColorImageFilter=/DCTEncode",
                "-dAutoFilterGrayImages=false", "-dGrayImageFilter=/DCTEncode"]
    if a.gray:
        cmd += ["-sColorConversionStrategy=Gray",
                "-dProcessColorModel=/DeviceGray"]
    cmd += [f"-sOutputFile={dst}"]
    if quality is not None:
        qf = jpeg_qfactor(quality)
        d = (f"<< /QFactor {qf} /Blend 1 /HSamples [2 1 1 2] /VSamples [2 1 1 2] >>")
        cmd += ["-c", f"<< /ColorImageDict {d} /GrayImageDict {d} >> setdistillerparams",
                "-f", src]
    else:
        cmd += [src]
    return cmd


def human(n):
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"


def process(gs, src, a):
    if a.inplace:
        out = src
    elif a.output and len(a.files) == 1:
        out = a.output
    else:
        out = os.path.splitext(src)[0] + ".min.pdf"

    before = os.path.getsize(src)
    fd, tmp = tempfile.mkstemp(suffix=".pdf")
    os.close(fd)
    try:
        r = subprocess.run(build_cmd(gs, src, tmp, a), capture_output=True, text=True)
        if r.returncode != 0:
            print(f"FAIL  {src}: {r.stderr.strip() or 'ghostscript error'}")
            return
        after = os.path.getsize(tmp)
        if after >= before and not a.force:
            hint = "" if (a.scan or a.recompress or a.quality) else "  Tip: try --scan (or -q 50)"
            print(f"SKIP  {src}: result not smaller ({human(before)} -> {human(after)}), kept original.{hint}")
            return
        shutil.move(tmp, out)
        pct = (1 - after / before) * 100
        print(f"OK    {src} -> {out}: {human(before)} -> {human(after)} ({pct:.0f}% smaller)")
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)


def main():
    p = argparse.ArgumentParser(description="Shrink PDFs with Ghostscript.")
    p.add_argument("files", nargs="+", help="input PDF(s)")
    p.add_argument("-p", "--preset", choices=PRESETS, default="ebook",
                   help="quality preset (default: ebook)")
    p.add_argument("--dpi", type=int, help="override image resolution, e.g. 100")
    p.add_argument("--gray", action="store_true", help="convert to grayscale")
    p.add_argument("--scan", action="store_true",
                   help="scanned-document mode: re-encode images at 150 dpi, quality 60")
    p.add_argument("-q", "--quality", type=int, metavar="1-100",
                   help="JPEG quality for images (forces re-encode; 40-70 is typical)")
    p.add_argument("--recompress", action="store_true",
                   help="re-encode already-compressed JPEG images")
    p.add_argument("--print-cmd", action="store_true", help="print the Ghostscript command and exit")
    p.add_argument("-o", "--output", help="output path (single input only)")
    p.add_argument("-i", "--inplace", action="store_true", help="overwrite the original")
    p.add_argument("-f", "--force", action="store_true",
                   help="write output even if it isn't smaller")
    a = p.parse_args()
    if a.quality is not None and not 1 <= a.quality <= 100:
        sys.exit("--quality must be between 1 and 100")
    if a.print_cmd:
        print(" ".join(build_cmd("gs", "IN.pdf", "OUT.pdf", a)))
        return

    gs = find_gs()
    for f in a.files:
        if not os.path.isfile(f):
            print(f"FAIL  {f}: file not found")
            continue
        process(gs, f, a)


if __name__ == "__main__":
    main()
