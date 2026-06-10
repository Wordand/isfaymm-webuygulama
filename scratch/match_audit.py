import re
import json
from pathlib import Path

root = Path('.')
ocr_dir = root / "services" / "ocr_text"

# 1. Parse ozelgeler_88_yeni.txt
content = (ocr_dir / "ozelgeler_88_yeni.txt").read_text(encoding="utf-8")
blocks = re.findall(r'\[\s*\{.*?\}\s*\]', content, re.DOTALL)
json_items = []
for b in blocks:
    json_items.extend(json.loads(b))

# 2. Parse raw texts to extract ozelge_no and date
extracted_files = {}
for txt_file in sorted(ocr_dir.glob("*.txt"), key=lambda p: p.name.lower()):
    if txt_file.name in ["birlesik.txt", "ozelgeler_88.txt", "ozelgeler_88_yeni.txt"]:
        continue
    text = txt_file.read_text(encoding="utf-8", errors="ignore")
    
    # Try to find ozelge no
    no_match = re.search(r'(?:Sayı|Özelge No|No|SAYI)\s*[:\-\s]*([^\n]+)', text, re.IGNORECASE)
    tarih_match = re.search(r'(?:Tarih|Özelge Tarihi|Tarihi)\s*[:\-\s]*([\d\./\s]+)', text, re.IGNORECASE)
    
    no_val = no_match.group(1).strip() if no_match else "Bulunamadı"
    tarih_val = tarih_match.group(1).strip() if tarih_match else "Bulunamadı"
    
    # Clean up value
    no_val = re.sub(r'[\r\n\t]', ' ', no_val).strip()
    tarih_val = re.sub(r'[\r\n\t]', ' ', tarih_val).strip()
    
    extracted_files[txt_file.name] = {
        "ozelge_no": no_val,
        "tarih": tarih_val,
        "title": text.split('\n')[0][:80].strip()
    }

print(f"Parsed {len(json_items)} items from ozelgeler_88_yeni.txt")
print(f"Parsed {len(extracted_files)} files from ocr_text")

# Let's see if we can do the matching and print mapping
mapping = {}
for idx, item in enumerate(json_items):
    ozelge_no = item.get("ozelge_no", "")
    tarih = item.get("tarih", "")
    konu = item.get("konu", "")

    no_parts = [p for p in re.split(r'[^a-zA-Z0-9]', ozelge_no) if len(p) >= 2]
    tarih_clean = tarih.replace(".", "/")

    candidates = []
    for filename, ext_data in extracted_files.items():
        # Get raw text
        ocr_clean = (ocr_dir / filename).read_text(encoding="utf-8", errors="ignore").lower()
        score = 0
        for part in no_parts:
            if part.lower() in ocr_clean:
                score += len(part) * 2
        if tarih in ocr_clean or tarih_clean in ocr_clean:
            score += 50
        konu_words = [w for w in re.split(r'\s+', re.sub(r'[^a-zA-Z0-9]', '', konu.lower())) if len(w) > 4]
        for w in konu_words[:12]:
            if w in ocr_clean:
                score += 5
        candidates.append((score, filename))
    candidates.sort(reverse=True)
    mapping[idx] = candidates

final_mapping = {}
used_files = set()
for idx in range(len(json_items)):
    for score, filename in mapping[idx]:
        if filename not in used_files:
            final_mapping[idx] = filename
            used_files.add(filename)
            break

# Print table
print("\nMapping Results:")
for idx, item in enumerate(json_items):
    filename = final_mapping.get(idx)
    ext_data = extracted_files.get(filename) if filename else {}
    print(f"JSON {idx:02d}: {item.get('ozelge_no')} ({item.get('tarih')}) -> File: {filename} [Extracted No: {ext_data.get('ozelge_no')}, Date: {ext_data.get('tarih')}]")
