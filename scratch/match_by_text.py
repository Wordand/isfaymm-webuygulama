import json
import re
from pathlib import Path

ROOT = Path(r"c:\Users\lalel\Desktop\webuygulama\webuygulama")
json_path = ROOT / "static" / "data" / "ozelgeler_yeni.json"
ocr_dir = ROOT / "services" / "ocr_text"

with open(json_path, "r", encoding="utf-8") as f:
    json_items = json.load(f)

txt_files = list(ocr_dir.glob("*.txt"))
ocr_texts = {}
for txt_file in txt_files:
    # skip composite/backup files
    if txt_file.name in ["birlesik.txt", "ozelgeler_88.txt", "ozelgeler_88_yeni.txt"]:
        continue
    text = txt_file.read_text(encoding="utf-8", errors="ignore")
    # Clean text to make matching easier
    clean = re.sub(r'\s+', ' ', text).lower()
    ocr_texts[txt_file.name] = clean

print(f"Loaded {len(ocr_texts)} OCR files.")

# Match each JSON item
mapping = {}
for i, item in enumerate(json_items):
    ozelge_no = item.get("ozelge_no", "")
    tarih = item.get("tarih", "")
    konu = item.get("konu", "")
    
    # Try to match by finding ozelge_no or tarih or part of konu in ocr texts
    best_match = None
    best_score = 0
    
    # Clean the query fields
    # e.g. B.07.1.GİB.4.25.15.01-2011-KVK-7215-2-10 -> search for parts of it
    no_parts = [p for p in re.split(r'[^a-zA-Z0-9]', ozelge_no) if len(p) >= 2]
    tarih_clean = tarih.replace(".", "/") # sometimes OCR is 02/11/2011 or 02.11.2011
    
    for filename, ocr_clean in ocr_texts.items():
        score = 0
        # check how many parts of ozelge_no are in ocr text
        for part in no_parts:
            if part.lower() in ocr_clean:
                score += len(part) * 2
        
        # check if date is in ocr text
        if tarih in ocr_clean or tarih_clean in ocr_clean:
            score += 50
        
        # check if topic matches
        # extract some keywords from konu
        konu_words = [w for w in re.split(r'\s+', re.sub(r'[^a-zA-Z0-9ğüşıöçĞÜŞİÖÇ ]', '', konu.lower())) if len(w) > 4]
        for w in konu_words[:10]:
            if w in ocr_clean:
                score += 5
        
        if score > best_score:
            best_score = score
            best_match = filename

    if best_score > 30: # reasonable threshold
        mapping[i] = (best_match, best_score)
    else:
        print(f"Low score match for item {i+1} ({ozelge_no}): best was {best_match} with score {best_score}")

print(f"Matched {len(mapping)} out of {len(json_items)}")

# Print a few samples of mapping
for idx in list(mapping.keys())[:10]:
    item = json_items[idx]
    match_file, score = mapping[idx]
    print(f"JSON: {item.get('ozelge_no')} ({item.get('tarih')}) -> OCR File: {match_file} (score: {score})")
