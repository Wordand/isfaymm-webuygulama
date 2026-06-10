import json
import re
from pathlib import Path

ROOT = Path(r"c:\Users\lalel\Desktop\webuygulama\webuygulama")

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

# 1. Load ozelgeler_88_yeni.txt and deduplicate by konu
txt_path = ROOT / "services" / "ocr_text" / "ozelgeler_88_yeni.txt"
raw = txt_path.read_text(encoding="utf-8").strip()
raw_combined = '[' + raw.lstrip('[').rstrip(']').replace(']\n[', ',').replace(']\r\n[', ',') + ']'
ai_data = json.loads(raw_combined)

seen_konu = set()
unique_ai_items = []
for item in ai_data:
    no = (item.get("ozelge_no") or "").strip()
    if "kv-2011-1-32/a-11" in no.lower():
        continue
    norm_konu = tr_normalize_compact(item.get("konu") or "")
    if norm_konu not in seen_konu:
        seen_konu.add(norm_konu)
        unique_ai_items.append(item)

print(f"Unique AI items from ozelgeler_88_yeni.txt: {len(unique_ai_items)}")

# 2. Load the 8 missing items from integrate_missing_summaries.py
# Let's import them or read them
import sys
sys.path.insert(0, str(ROOT))
from scratch.integrate_missing_summaries import missing_items

# Deduplicate missing items just in case
unique_missing = []
for item in missing_items:
    norm_konu = tr_normalize_compact(item.get("konu") or "")
    if norm_konu not in seen_konu:
        seen_konu.add(norm_konu)
        unique_missing.append(item)
    else:
        print(f"Warning: missing item '{item.get('ozelge_no')}' subject already exists in AI data!")

all_summaries = unique_ai_items + unique_missing
print(f"Total summaries (AI + missing): {len(all_summaries)}")

# 3. Load all physical files
ocr_dir = ROOT / "services" / "ocr_text"
txt_files = list(ocr_dir.glob("*.txt"))
ocr_texts = {}
for txt_file in txt_files:
    if txt_file.name in ["birlesik.txt", "ozelgeler_88.txt", "ozelgeler_88_yeni.txt"]:
        continue
    ocr_texts[txt_file.name] = txt_file.read_text(encoding="utf-8", errors="ignore")

print(f"Total physical OCR files: {len(ocr_texts)}")

# 4. Map summaries to physical files using global-score matching
all_pairs = []
for idx, item in enumerate(all_summaries):
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

    for filename, ocr_text in ocr_texts.items():
        ocr_clean = tr_normalize(ocr_text)
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

print(f"Mapped {len(final_mapping)} summaries to physical files.")
unmatched_files = sorted(set(ocr_texts.keys()) - used_files)
print(f"Unmatched physical files ({len(unmatched_files)}):")
for f in unmatched_files:
    # Get metadata from the first few lines of the text file
    text_lines = ocr_texts[f].splitlines()
    non_empty_lines = [l.strip() for l in text_lines if l.strip()][:15]
    print(f"\n--- File: {f} ---")
    for l in non_empty_lines:
        print("  ", l)
