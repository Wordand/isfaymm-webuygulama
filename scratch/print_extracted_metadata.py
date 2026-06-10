import re
from pathlib import Path

root = Path('.')
ocr_dir = root / "services" / "ocr_text"

extracted = []
for txt_file in sorted(ocr_dir.glob("*.txt"), key=lambda p: p.name.lower()):
    if txt_file.name in ["birlesik.txt", "ozelgeler_88.txt", "ozelgeler_88_yeni.txt"]:
        continue
    text = txt_file.read_text(encoding="utf-8", errors="ignore")
    
    no_match = re.search(r'(?:Sayı|Özelge No|No|SAYI)\s*[:\-\s]*([^\n]+)', text, re.IGNORECASE)
    tarih_match = re.search(r'(?:Tarih|Özelge Tarihi|Tarihi)\s*[:\-\s]*([\d\./\s]+)', text, re.IGNORECASE)
    
    no_val = no_match.group(1).strip() if no_match else "Bulunamadı"
    tarih_val = tarih_match.group(1).strip() if tarih_match else "Bulunamadı"
    
    no_val = re.sub(r'[\r\n\t]', ' ', no_val).strip()
    tarih_val = re.sub(r'[\r\n\t]', ' ', tarih_val).strip()
    
    extracted.append((txt_file.name, no_val, tarih_val))

for item in extracted:
    print(f"{item[0]}: {item[1]} ({item[2]})")
