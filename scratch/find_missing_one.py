import json
import re
import sys
from pathlib import Path

ROOT = Path(r"c:\Users\lalel\Desktop\webuygulama\webuygulama")
sys.path.insert(0, str(ROOT))

def tr_lower(text):
    mapping_dict = {'I': 'ı', 'İ': 'i', 'Ö': 'ö', 'Ü': 'ü', 'Ş': 'ş', 'Ğ': 'ğ', 'Ç': 'ç'}
    for k, v in mapping_dict.items():
        text = text.replace(k, v)
    return text.lower()

def tr_normalize(text):
    text = tr_lower(text)
    tr_map = str.maketrans('çğıöşüâîû', 'cgiosuaiu')
    text = text.translate(tr_map)
    text = re.sub(r'[^a-z0-9\s]', ' ', text)
    return re.sub(r'\s+', ' ', text).strip()

def tr_normalize_compact(text):
    return re.sub(r'[^a-z0-9]', '', tr_normalize(text))

# Load the 87 items in ozelgeler_yeni.json
json_path = ROOT / "static" / "data" / "ozelgeler_yeni.json"
with open(json_path, "r", encoding="utf-8") as f:
    json_items = json.load(f)

# Load all physical files
ocr_dir = ROOT / "services" / "ocr_text"
txt_files = list(ocr_dir.glob("*.txt"))
ocr_texts = {}
for txt_file in txt_files:
    if txt_file.name in ["birlesik.txt", "ozelgeler_88.txt", "ozelgeler_88_yeni.txt"]:
        continue
    ocr_texts[txt_file.name] = tr_normalize(txt_file.read_text(encoding="utf-8", errors="ignore"))

# Run the same bipartite matching as services/ozelge_service.py
all_pairs = []
for idx, item in enumerate(json_items):
    ozelge_no = item.get("ozelge_no", "")
    tarih = item.get("tarih", "")
    konu = item.get("konu", "")
    mukellef_sorusu = item.get("mukellef_sorusu", "")

    no_clean = re.sub(r'[^a-zA-Z0-9]', '', ozelge_no).lower()
    parts = [p for p in re.split(r'[^a-zA-Z0-9]', ozelge_no) if len(p) >= 2]
    tarih_clean = tarih.replace(".", "/")
    
    norm_konu = tr_normalize(konu)
    norm_soru = tr_normalize(mukellef_sorusu)
    combined_words = re.split(r'\s+', norm_konu + ' ' + norm_soru)
    keywords = [w for w in combined_words if len(w) > 4]

    for filename, ocr_clean in ocr_texts.items():
        score = 0
        if no_clean and no_clean in ocr_clean:
            score += 1000
        for part in parts:
            if part.lower() in ocr_clean:
                score += len(part) * 10
        
        stem = filename.replace(".txt", "").lower()
        if parts and (stem in parts[-1].lower() or parts[-1].lower() in stem):
            score += 500
            
        if tarih and (tarih in ocr_clean or tarih_clean in ocr_clean):
            score += 300
            
        content_score = sum(1 for w in keywords if w in ocr_clean)
        score += content_score

        all_pairs.append((score, idx, filename))

all_pairs.sort(key=lambda x: x[0], reverse=True)

final_mapping = {}
assigned_idx = set()
used_files = set()

for score, idx, filename in all_pairs:
    if idx not in assigned_idx and filename not in used_files:
        assigned_idx.add(idx)
        used_files.add(filename)
        final_mapping[idx] = filename

unmatched = sorted(set(ocr_texts.keys()) - used_files)
print(f"Total physical files: {len(ocr_texts)}")
print(f"Matched json items: {len(final_mapping)}")
print(f"Unmatched physical files: {unmatched}")
if unmatched:
    print("\nContent of the unmatched physical file:")
    print(ocr_texts[unmatched[0]][:2000])
