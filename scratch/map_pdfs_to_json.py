import json
import re
from pathlib import Path

ROOT = Path(r"c:\Users\lalel\Desktop\webuygulama\webuygulama")
json_path = ROOT / "static" / "data" / "ozelgeler_yeni.json"
ocr_dir = ROOT / "services" / "ocr_text"
pdf_dir = ROOT / "services" / "ozelgeler"

with open(json_path, "r", encoding="utf-8") as f:
    json_items = json.load(f)

# Build a map of normalized ozelge_no -> JSON item
def normalize_no(no):
    if not no:
        return ""
    # Normalize characters, spaces, dashes
    no = no.replace("İ", "I").replace("ı", "i").replace("Ğ", "G").replace("ğ", "g")
    no = no.replace("Ö", "O").replace("ö", "o").replace("Ş", "S").replace("ş", "s")
    no = no.replace("Ç", "C").replace("ç", "c")
    no = re.sub(r'[^a-zA-Z0-9]', '', no)
    return no.lower().strip()

json_map = {}
for item in json_items:
    norm = normalize_no(item.get("ozelge_no"))
    if norm:
        json_map[norm] = item

# Now check OCR files
txt_files = list(ocr_dir.glob("*.txt"))
matched_count = 0
mapping = {}

for txt_file in txt_files:
    text = txt_file.read_text(encoding="utf-8", errors="ignore")
    # Try different regexes to find ozelge no
    no_match = re.search(r"Özelge No\s*(.*?)\n", text, re.IGNORECASE)
    no = no_match.group(1).strip() if no_match else ""
    if not no:
        no_match = re.search(r"Sayı\s*(.*?)\n", text, re.IGNORECASE)
        no = no_match.group(1).strip() if no_match else ""
    
    norm_no = normalize_no(no)
    pdf_name = txt_file.stem + ".pdf"
    pdf_path = pdf_dir / pdf_name
    
    if norm_no in json_map:
        matched_count += 1
        mapping[pdf_name] = json_map[norm_no]["ozelge_no"]
    else:
        # Try finding by date or subject or other ways
        # Let's print unmatched
        print(f"Unmatched OCR file: {txt_file.name}, extracted No: {no}")

print(f"\nMatched: {matched_count} out of {len(txt_files)}")
print(f"JSON items size: {len(json_items)}")
