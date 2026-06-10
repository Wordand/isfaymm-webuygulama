from pathlib import Path

ROOT = Path(r"c:\Users\lalel\Desktop\webuygulama\webuygulama")
ocr_dir = ROOT / "services" / "ocr_text"

unmatched_files = [
    "26829.txt",
    "28.txt",
    "280.txt",
    "47285862-010.01[32-201209]-19.txt",
    "49.txt",
    "490013.txt",
    "49717.txt",
    "531740.txt",
    "561630.txt",
    "57172.txt",
    "63611781-125[32A-20134 ]-10.txt",
    "67630374-125[2013-7]-5.txt",
    "713.txt",
    "7831.txt",
    "82.txt",
    "874.txt",
    "E.22727.txt",
    "E.8068.txt"
]

out = []
for f in unmatched_files:
    p = ocr_dir / f
    if p.exists():
        text = p.read_text(encoding="utf-8", errors="ignore")
        out.append(f"=========================================\nFILE: {f}\n=========================================\n")
        out.append(text[:3000])
        out.append("\n\n")
    else:
        out.append(f"FILE NOT FOUND: {f}\n\n")

out_path = ROOT / "scratch" / "unmatched_contents.txt"
out_path.write_text("".join(out), encoding="utf-8")
print("Wrote unmatched contents to scratch/unmatched_contents.txt")
