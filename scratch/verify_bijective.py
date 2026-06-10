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
    if txt_file.name in ["birlesik.txt", "ozelgeler_88.txt", "ozelgeler_88_yeni.txt"]:
        continue
    text = txt_file.read_text(encoding="utf-8", errors="ignore")
    ocr_texts[txt_file.name] = re.sub(r'\s+', ' ', text).lower()

# For each JSON item, find all matching scores and sort
mapping = {}
assigned_files = set()
for idx, item in enumerate(json_items):
    ozelge_no = item.get("ozelge_no", "")
    tarih = item.get("tarih", "")
    konu = item.get("konu", "")
    
    no_parts = [p for p in re.split(r'[^a-zA-Z0-9]', ozelge_no) if len(p) >= 2]
    tarih_clean = tarih.replace(".", "/")
    
    candidates = []
    for filename, ocr_clean in ocr_texts.items():
        score = 0
        for part in no_parts:
            if part.lower() in ocr_clean:
                score += len(part) * 2
        if tarih in ocr_clean or tarih_clean in ocr_clean:
            score += 50
        
        # topic words
        konu_words = [w for w in re.split(r'\s+', re.sub(r'[^a-zA-Z0-9ğüşıöçĞÜŞİÖÇ ]', '', konu.lower())) if len(w) > 4]
        for w in konu_words[:12]:
            if w in ocr_clean:
                score += 5
        
        candidates.append((score, filename))
    
    candidates.sort(reverse=True)
    mapping[idx] = candidates

# Resolve conflict / greedy matching
final_mapping = {}
used_files = set()
# Sort json items by their best score margin to resolve conflicts, or just run a simple match
# Let's see if we just greedily match:
for idx in range(len(json_items)):
    # Find first candidate not used
    for score, filename in mapping[idx]:
        if filename not in used_files:
            final_mapping[idx] = (filename, score)
            used_files.add(filename)
            break

print(f"Greedy matching complete. Matched: {len(final_mapping)} / {len(json_items)}")
print(f"Unused OCR files: {set(ocr_texts.keys()) - used_files}")

# Print all mappings
for idx, (filename, score) in sorted(final_mapping.items()):
    item = json_items[idx]
    print(f"Index {idx:2d} | JSON: {item.get('ozelge_no')} | PDF: {filename.replace('.txt', '.pdf')} (Score: {score})")
