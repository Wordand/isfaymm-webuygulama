import re
from pathlib import Path

ROOT = Path(r"c:\Users\lalel\Desktop\webuygulama\webuygulama")
ocr_dir = ROOT / "services" / "ocr_text"

unmatched_files = [
    "26829.txt",
    "28.txt",
    "280.txt",
    "47285862-010.01[32-201209]-19.txt",
    "49.txt",
    "490013.txt",
    "49717.txt",
    "531740.txt",
    "561630.txt",
    "57172.txt",
    "63611781-125[32A-20134 ]-10.txt",
    "67630374-125[2013-7]-5.txt",
    "713.txt",
    "7831.txt",
    "82.txt",
    "874.txt",
    "E.22727.txt",
    "E.8068.txt"
]

out = []
for f in unmatched_files:
    p = ocr_dir / f
    if not p.exists():
        continue
    text = p.read_text(encoding="utf-8", errors="ignore")
    
    # Clean text to remove double lines/whitespace
    text_clean = re.sub(r'\s+', ' ', text)
    
    # Try to extract the ruling number and date
    no_match = re.search(r'(?:Özelge No|Sayı)\s*[:\-]?\s*([^\s]+)', text, re.IGNORECASE)
    tarih_match = re.search(r'(?:Özelge Tarihi|Tarih)\s*[:\-]?\s*([0-9.]{10})', text, re.IGNORECASE)
    
    no = no_match.group(1) if no_match else "Bilinmiyor"
    tarih = tarih_match.group(1) if tarih_match else "Bilinmiyor"
    
    # Find question part (usually starts after "İlgi" or "Konu")
    question = ""
    q_marker = re.search(r'ilgide kayıtlı özelge talep form[a-z\s]+', text_clean, re.IGNORECASE)
    if q_marker:
        start_idx = q_marker.start()
        # Take the next 1000 characters
        question = text_clean[start_idx:start_idx+1200]
    else:
        # Fallback: take first 1000 chars after Konu
        konu_idx = text_clean.lower().find("konu")
        if konu_idx != -1:
            question = text_clean[konu_idx:konu_idx+1200]
        else:
            question = text_clean[:1200]
            
    # Find answer part (usually near the end, starts with "Buna göre" or "Bu hüküm ve" or "Yukarıda yer alan")
    answer = ""
    ans_markers = [
        r'bu hüküm ve açıklamalara göre',
        r'bu hüküm ve açıklamalar çerçevesinde',
        r'yukarıda yer alan hüküm ve açıklamalar çerçevesinde',
        r'buna göre',
        r'sonuç olarak'
    ]
    best_idx = -1
    for marker in ans_markers:
        matches = list(re.finditer(marker, text_clean, re.IGNORECASE))
        if matches:
            # We want the last one, or the one closest to the end that is not at the very end
            for m in matches:
                idx = m.start()
                if idx > best_idx and idx < len(text_clean) - 100:
                    best_idx = idx
                    
    if best_idx != -1:
        answer = text_clean[best_idx:best_idx+1500]
    else:
        # Fallback: last 1500 characters
        answer = text_clean[-1500:]
        
    out.append(f"=========================================\n")
    out.append(f"FILE: {f}\n")
    out.append(f"ÖZELGE NO: {no}\n")
    out.append(f"TARİH: {tarih}\n")
    out.append(f"QUESTION CHUNK:\n{question}\n\n")
    out.append(f"ANSWER CHUNK:\n{answer}\n")
    out.append(f"=========================================\n\n")

out_path = ROOT / "scratch" / "extracted_details.txt"
out_path.write_text("".join(out), encoding="utf-8")
print("Wrote details to scratch/extracted_details.txt")
