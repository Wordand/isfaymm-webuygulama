import re
import json
from pathlib import Path

root = Path('.')
content = (root / "services" / "ocr_text" / "ozelgeler_88_yeni.txt").read_text(encoding="utf-8")
blocks = re.findall(r'\[\s*\{.*?\}\s*\]', content, re.DOTALL)

yeni_data = []
seen_keys = set()
for b in blocks:
    for item in json.loads(b):
        key = (item.get("ozelge_no") or "").strip().lower()
        if not key:
            key = (item.get("konu") or "").strip().lower()
        if key not in seen_keys:
            seen_keys.add(key)
            yeni_data.append(item)

ocr_dir = root / "services" / "ocr_text"
txt_files = list(ocr_dir.glob("*.txt"))
ocr_texts = {}
for txt_file in txt_files:
    if txt_file.name in ["birlesik.txt", "ozelgeler_88.txt", "ozelgeler_88_yeni.txt"]:
        continue
    ocr_texts[txt_file.name] = txt_file.read_text(encoding="utf-8", errors="ignore")

# Run mapping for 81 unique items
mapping = {}
for idx, item in enumerate(yeni_data):
    ozelge_no = item.get("ozelge_no", "")
    tarih = item.get("tarih", "")
    konu = item.get("konu", "")

    no_parts = [p for p in re.split(r'[^a-zA-Z0-9]', ozelge_no) if len(p) >= 2]
    tarih_clean = tarih.replace(".", "/")

    candidates = []
    for filename, ocr_text in ocr_texts.items():
        ocr_clean = ocr_text.lower()
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
for idx in range(len(yeni_data)):
    for score, filename in mapping[idx]:
        if filename not in used_files:
            final_mapping[idx] = filename
            used_files.add(filename)
            break

all_files = set(ocr_texts.keys())
unmatched_files = sorted(all_files - used_files)
print("Total unmatched files:", len(unmatched_files))
for f in unmatched_files:
    text = ocr_texts[f][:300]
    print(f"File: {f}")
    print(text)
    print("-" * 50)
