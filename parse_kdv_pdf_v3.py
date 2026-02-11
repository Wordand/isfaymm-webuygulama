#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
KDV Genel Uygulama Tebligi - Gelismis PDF Parser v3
Font bilgilerini (Bold/Normal) kullanarak baslik hiyerarsisini dogru kurar.
Benzersiz UID sistemi, dipnot temizleme ve paragraf formatlama iceriyor.

Duzeltmeler v3:
- Roman numeral regex duzeltildi (V ve IV karismasi onlendi)
- PDF sonundaki form/belge sablonlari filtreleniyor
- Cok satira yayilan basliklar birlestirilmeli
- Ğ harfi L1 yakalamaya eklendi
"""

import pdfplumber
import json
import re
import os
import sys
import warnings

warnings.filterwarnings("ignore")

PDF_PATH = r"C:\Users\lalel\Desktop\webuygulama\webuygulama\kdvtebligi.pdf"
JSON_OUTPUT = r"C:\Users\lalel\Desktop\webuygulama\webuygulama\static\data\kdv_tebligi.json"
BACKUP_PATH = JSON_OUTPUT + ".before_reparse"

# Teblig iceriginin bittigi sayfa (form ve ek belge sablonlari baslamadan onceki sayfa)
# Bu sayfa sonrasindan sadece form, fatura sablonlari vs. var -> atla
MAX_CONTENT_PAGE = 385  # Yaklasik, calistiktan sonra ayarlayabiliriz


def clean_footnote_from_title(title):
    """Basliktan dipnot numaralarini temizle."""
    if not title:
        return title
    # Harf + rakam(lar) ile biten ve boslukla ayrilmis footnote numaralari
    cleaned = re.sub(r'(?<=[a-zA-ZçğıöşüÇĞİÖŞÜ)ıİ])\s*\d{1,4}$', '', title)
    # Bazen boslukla ayrilmis: "Beyani 107" -> "Beyani"
    cleaned = re.sub(r'\s+\d{2,4}$', '', cleaned) 
    return cleaned.strip()


def format_content(text):
    """Icerik metnine uygun paragraf kesmeleri ekle"""
    if not text or len(text.strip()) < 10:
        return text.strip() if text else ""
    
    # Bent isaretleri: a), b), c) gibi
    text = re.sub(r'(?<=[.;:]) +((?:[a-hıçğöşü]\)) )', r'\n\n\1', text)
    
    # Ornek bolumleri
    text = re.sub(r'(?<=[\s.]) *(Örnek\s*\d*\s*:)', r'\n\n\1', text)
    
    # Dipnot numaralari
    text = re.sub(r'(?<=[.)]) +(\d{1,2} \d+ Seri No)', r'\n\n\1', text)
    text = re.sub(r'(?<=[.)]) +(\d{1,2} \d{2}[./]\d{2}[./]\d{4} tarihli)', r'\n\n\1', text)
    
    # Tire ile baslayan maddeler
    text = re.sub(r'(?<=[.:;]) +(- [A-ZÇĞİÖŞÜa-zçğıöşü])', r'\n\n\1', text)
    
    # Gecis ifadeleri
    for phrase in ['Buna göre', 'Ancak', 'Diğer taraftan', 'Öte yandan', 'Ayrıca', 'Dolayısıyla']:
        text = re.sub(r'(?<=[.]) +(' + phrase + r'[, ])', r'\n\n\1', text)
    
    # Kanun referanslari
    text = re.sub(r'(?<=[.]) +(3065 sayılı Kanunun \(\d)', r'\n\n\1', text)
    
    # Coklu newline temizligi
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    return text.strip()


def extract_lines_with_style(pdf):
    """PDF'den tum satirlari font bilgileriyle birlikte cikar"""
    all_lines = []
    
    for page_num, page in enumerate(pdf.pages):
        # Icerik sayfa sinirini gecme
        if page_num + 1 > MAX_CONTENT_PAGE:
            break
            
        try:
            words = page.extract_words(extra_attrs=["fontname", "size"])
        except:
            continue
        
        if not words:
            continue
        
        # Satirlari olustur (ayni y koordinatindaki kelimeleri birlestir)
        lines_on_page = []
        current_line_words = []
        current_y = None
        
        for w in words:
            word_y = round(w.get("top", 0), 1)
            
            if current_y is None:
                current_y = word_y
            
            if abs(word_y - current_y) > 3:
                if current_line_words:
                    lines_on_page.append(current_line_words)
                current_line_words = [w]
                current_y = word_y
            else:
                current_line_words.append(w)
        
        if current_line_words:
            lines_on_page.append(current_line_words)
        
        # Satirlari isle
        for line_words in lines_on_page:
            text = " ".join(w.get("text", "") for w in line_words).strip()
            
            bold_count = sum(1 for w in line_words if "Bold" in w.get("fontname", ""))
            total_count = len(line_words)
            is_bold = bold_count > total_count * 0.5
            
            avg_size = sum(w.get("size", 11) for w in line_words) / total_count if total_count else 11
            
            if text and not text.isdigit():
                all_lines.append({
                    "text": text,
                    "bold": is_bold,
                    "size": avg_size,
                    "page": page_num + 1
                })
    
    return all_lines


def classify_header(text):
    """Bold bir satirin baslik seviyesini belirle.
    Returns: (level_name, depth, id, title) or None
    
    Hiyerarsi:
    L0: Roman (I, II, III, IV, V, VI) 
    L1: Harf (A, B, C, ..., Ğ) - Turkce dahil
    L2: Sayi (1, 2, 3)
    L3: AltSayi (1.1, 2.3)
    L4: AltAltSayi (1.1.1, 2.3.4)
    """
    
    # Sayfa basligi filtrele
    if "RESMİ GAZETE" in text.upper() or "RESM" in text:
        return None
    if re.match(r'^\d+ \w+ \d{4}', text):
        return None
    if text.startswith("Sayı") or text.startswith("Say"):
        return None
    if len(text) < 2 or len(text) > 250:
        return None
    
    # Formatlara ait cop satirlari
    if re.match(r'^[A-Z]\s+[A-Z]\s+[A-Z]\s+[A-Z]', text):  # "T a r i h :" gibi
        return None
    if "FATURA" in text and len(text) < 20:
        return None
    
    # ONCELIK: En spesifik pattern'den en geneline
    
    # L4: X.Y.Z formati - "1.1.1" veya "1.1.1." 
    m = re.match(r'^(\d{1,2}\.\d{1,2}\.\d{1,2})\.?\s+(.+)$', text)
    if m:
        return ('L4', 4, m.group(1).strip(), m.group(2).strip())
    
    # L3: X.Y formati - "1.1" veya "1.1." 
    m = re.match(r'^(\d{1,2}\.\d{1,2})\.?\s+(.+)$', text)
    if m:
        return ('L3', 3, m.group(1).strip(), m.group(2).strip())
    
    # L0: Roman numeral - SADECE tam Roman numeraller 
    # "V - VERGININ" gibi ama "Vergi ilişkin" gibi normal cumleleri yakalamasin
    # V harfi tek basina sorun yaratabilir, o yuzden "V" icin ozel kontrol
    m = re.match(r'^(VI|IV|V|III|II|I)\s*[-–.]\s+(.+)$', text)
    if m:
        roman = m.group(1)
        title = m.group(2).strip()
        # Roman numeral basliklar genellikle BUYUK HARF ile devam eder
        if title and (title[0].isupper() or title[0] in 'İÖÜÇŞĞ'):
            return ('L0', 0, roman, title)
    
    # L1: Buyuk harf - "A -" veya "B." veya "Ğ -" gibi
    # Ama "V -" gibi Roman numeral'i L0 olarak yakaladigimiz icin
    # burada V'yi dahil etmeyelim
    m = re.match(r'^([A-UW-ZÇĞİÖŞÜĞ])\s*[-–.]\s+(.+)$', text)
    if m:
        letter = m.group(1)
        title = m.group(2).strip()
        # Tek harfli baslik kontrolu: baslik makul uzunlukta ve buyuk harfle baslayan 
        if title and len(title) > 2:
            return ('L1', 1, letter, title)
    
    # L2: Tek sayi - "1." veya "1 -" 
    m = re.match(r'^(\d{1,2})\s*[-–.]\s+(.+)$', text)
    if m:
        num = m.group(1)
        title = m.group(2).strip()
        if title and len(title) > 2:
            return ('L2', 2, num, title)
    
    return None


def build_hierarchy(lines):
    """Satirlardan hiyerarsi olustur"""
    root = []
    stack = []  # (depth, node) tuples
    last_content_target = None
    
    # Cok satirlik baslik birlestirme
    pending_bold_text = ""
    pending_bold_line = None
    
    for i, line in enumerate(lines):
        text = line["text"].strip()
        
        # Sayfa basligi filtreleme
        if "RESMİ GAZETE" in text.upper() or "RESM" in text:
            continue
        if re.match(r'^\d+ \w+ \d{4}', text):
            continue
        if text.startswith("Sayı") and len(text) < 20:
            continue
        # Form sablonu filtreleme
        if re.match(r'^[A-Z]\s+[A-Z]\s+[A-Z]', text) and len(text) > 20:
            continue
        
        if line["bold"]:
            # Baslik adayi
            header = classify_header(text)
            
            if header:
                level_name, depth, node_id, title = header
                
                node = {
                    "id": node_id,
                    "title": clean_footnote_from_title(title),
                    "content": "",
                    "sub": []
                }
                
                # Stack'i bu derinlige kadar kes
                while stack and stack[-1][0] >= depth:
                    stack.pop()
                
                if not stack:
                    root.append(node)
                else:
                    parent = stack[-1][1]
                    parent["sub"].append(node)
                
                stack.append((depth, node))
                last_content_target = node
            else:
                # Bold ama baslik degil - icerige ekle (bold metin)
                if last_content_target is not None:
                    if last_content_target["content"]:
                        last_content_target["content"] += " " + text
                    else:
                        last_content_target["content"] = text
        else:
            # Normal metin - son basligin icerigine ekle
            if last_content_target is not None:
                if last_content_target["content"]:
                    last_content_target["content"] += " " + text
                else:
                    last_content_target["content"] = text
    
    return root


def add_uid_recursive(items, parent_uid=""):
    """Her ogeye benzersiz uid ekle"""
    for item in items:
        if parent_uid:
            item["uid"] = f"{parent_uid}/{item['id']}"
        else:
            item["uid"] = item["id"]
        
        if item.get("sub"):
            add_uid_recursive(item["sub"], item["uid"])


def format_all_content(items):
    """Tum icerikleri formatla"""
    for item in items:
        if item.get("content"):
            item["content"] = format_content(item["content"])
        if item.get("sub"):
            format_all_content(item["sub"])


def remove_junk_items(items):
    """Form sablon ogeleri ve cop verileri kaldir"""
    cleaned = []
    for item in items:
        title = item.get("title", "")
        item_id = item.get("id", "")
        
        # Cop filtreleme
        if re.match(r'^[A-Z]\s+[A-Z]\s+[A-Z]', title):  # Bosluklarla ayrilmis harfler
            continue
        if "FATURA" in title and len(title) < 20:
            continue
        if title.startswith("a r i h") or title.startswith("e r i"):
            continue
        if "İ M A L A T" in title or "T O P L A M" in title:
            continue
        if "A L I C I" in title or "S A T I C I" in title:
            continue
        if "Nakden" in title and len(title) < 30:
            continue
        if "Banka Hesab" in title and len(title) < 50:
            continue
        if "7 x 8" in title:
            continue
        if "DAMGA VERGİSİ" in title and len(title) < 20:
            continue
        if title.startswith("Düzenlenme") and len(title) < 20:
            continue
        if title.startswith("Tarihi") and len(title) < 15:
            continue
        if "İhale Tutanağ" in title and len(title) < 50:
            continue
        if "Bedelin Tahsil" in title and len(title) < 50:
            continue
        
        # Alt ogeleri de temizle
        if item.get("sub"):
            item["sub"] = remove_junk_items(item["sub"])
        
        cleaned.append(item)
    
    return cleaned


def count_items(items):
    total = len(items)
    for item in items:
        if item.get("sub"):
            total += count_items(item["sub"])
    return total


def print_tree(items, depth=0, max_depth=3):
    for item in items:
        prefix = "  " * depth
        uid = item.get("uid", item["id"])
        title = item.get("title", "")[:60]
        sub_count = len(item.get("sub", []))
        has_content = "+" if item.get("content", "").strip() else "-"
        print(f"{prefix}[{has_content}] {uid} | {title} (sub:{sub_count})")
        
        if item.get("sub") and depth < max_depth:
            print_tree(item["sub"], depth + 1, max_depth)


def main():
    print("=" * 70)
    print("KDV Genel Uygulama Tebligi - PDF Parser v3")
    print("=" * 70)
    
    # Yedek
    if os.path.exists(JSON_OUTPUT):
        import shutil
        shutil.copy2(JSON_OUTPUT, BACKUP_PATH)
        print(f"Yedek: {BACKUP_PATH}")
    
    # PDF ac
    print(f"\nPDF: {PDF_PATH}")
    pdf = pdfplumber.open(PDF_PATH)
    print(f"Sayfa: {len(pdf.pages)}")
    
    # Satirlari cikar
    print("\nSatirlar cikariliyor...")
    lines = extract_lines_with_style(pdf)
    bold_count = sum(1 for l in lines if l["bold"])
    print(f"Satir: {len(lines)}, Bold: {bold_count}")
    
    pdf.close()
    
    # Hiyerarsi olustur
    print("\nHiyerarsi olusturuluyor...")
    data = build_hierarchy(lines)
    print(f"Ust seviye: {len(data)}")
    
    # Cop verileri kaldir
    print("Cop veriler temizleniyor...")
    for item in data:
        if item.get("sub"):
            item["sub"] = remove_junk_items(item["sub"])
    data = remove_junk_items(data)
    
    # UID ekle
    add_uid_recursive(data)
    
    # Icerikleri formatla
    format_all_content(data)
    
    # Istatistikler
    total = count_items(data)
    print(f"Toplam: {total} oge")
    
    # Agac
    print("\n--- YAPI (2 seviye) ---")
    print_tree(data, max_depth=2)
    
    # Kaydet
    with open(JSON_OUTPUT, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print(f"\nKaydedildi: {JSON_OUTPUT}")
    print("Bitti!")


if __name__ == "__main__":
    main()
