import json
from pathlib import Path

ROOT = Path(r"c:\Users\lalel\Desktop\webuygulama\webuygulama")
json_path = ROOT / "static" / "data" / "ozelgeler_yeni.json"
pdf_dir = ROOT / "services" / "ozelgeler"

with open(json_path, "r", encoding="utf-8") as f:
    data = json.load(f)

print(f"Total items in JSON: {len(data)}")
pdf_files = list(pdf_dir.glob("*.pdf"))
print(f"Total PDF files: {len(pdf_files)}")

# Print first 3 items in JSON
for i, item in enumerate(data[:3]):
    print(f"\nItem {i+1}:")
    print(f"  ozelge_no: {item.get('ozelge_no')}")
    print(f"  tarih: {item.get('tarih')}")
    print(f"  konu: {item.get('konu')[:60]}...")
    print(f"  etiketler: {item.get('etiketler')}")
