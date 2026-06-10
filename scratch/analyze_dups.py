import json
import re
from pathlib import Path

ROOT = Path(r"c:\Users\lalel\Desktop\webuygulama\webuygulama")

def tr_normalize(text):
    text = text.lower()
    mapping_dict = {'I': 'ı', 'İ': 'i', 'Ö': 'ö', 'Ü': 'ü', 'Ş': 'ş', 'Ğ': 'ğ', 'Ç': 'ç'}
    for k, v in mapping_dict.items():
        text = text.replace(k, v)
    tr_map = str.maketrans('çğıöşüâîû', 'cgiosuaiu')
    text = text.translate(tr_map)
    text = re.sub(r'[^a-z0-9]', '', text)
    return text.strip()

txt_path = ROOT / "services" / "ocr_text" / "ozelgeler_88_yeni.txt"
raw = txt_path.read_text(encoding="utf-8").strip()
raw_combined = '[' + raw.lstrip('[').rstrip(']').replace(']\n[', ',').replace(']\r\n[', ',') + ']'
data = json.loads(raw_combined)

print("Total raw items loaded:", len(data))

# Find duplicates by normalized konu
seen_konu = {}
for idx, item in enumerate(data):
    konu = item.get("konu") or ""
    norm_konu = tr_normalize(konu)
    if norm_konu not in seen_konu:
        seen_konu[norm_konu] = []
    seen_konu[norm_konu].append((idx, item))

duplicates_found = 0
for norm_konu, items in seen_konu.items():
    if len(items) > 1:
        duplicates_found += 1
        print(f"\nDuplicate Group (Normalized konu hash: {norm_konu[:30]}...):")
        for idx, item in items:
            print(f"  Index: {idx} | ozelge_no: {item.get('ozelge_no')} | tarih: {item.get('tarih')} | konu: {item.get('konu')[:100]}")

print("\nNumber of unique konusu:", len(seen_konu))
print("Number of duplicate groups:", duplicates_found)
