#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
KDV Genel Uygulama Tebligi - Gelismis PDF Parser v2
Font bilgilerini (Bold/Normal) kullanarak baslik hiyerarsisini dogru kurar.
Benzersiz UID sistemi, dipnot temizleme ve paragraf formatlama iceriyor.
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

# ============================================================
# BASLIKLARIN TESPITI ICIN REGEX KALIPLARI
# ============================================================
# Hiyerarsi: Roman (I,II) > Harf (A,B,C) > Sayi (1,2,3) > AltSayi (1.1) > AltAltSayi (1.1.1)
HEADER_PATTERNS = [
    # Level 0: Roman numerals - "I -" veya "II." gibi
    ('L0', re.compile(r'^(I{1,3}|IV|V|VI)\s*[-.]?\s+(.+)$')),
    
    # Level 1: Buyuk harfler - "A -" veya "B." gibi (Turkce harfler dahil)
    ('L1', re.compile(r'^([A-ZÇĞİÖŞÜ])\s*[-.]?\s+(.+)$')),
    
    # Level 2: Tek sayi - "1." veya "1 -" gibi
    ('L2', re.compile(r'^(\d{1,2})\s*[-.]?\s+(.+)$')),
    
    # Level 3: X.Y formati - "1.1" veya "1.1." gibi
    ('L3', re.compile(r'^(\d{1,2}\.\d{1,2})\.?\s+(.+)$')),
    
    # Level 4: X.Y.Z formati - "1.1.1" veya "1.1.1." gibi
    ('L4', re.compile(r'^(\d{1,2}\.\d{1,2}\.\d{1,2})\.?\s+(.+)$')),
]

LEVEL_DEPTH = {'L0': 0, 'L1': 1, 'L2': 2, 'L3': 3, 'L4': 4}


def clean_footnote_from_title(title):
    """Basliktan dipnot numaralarini temizle.
    'Istisnanin Kapsami ve Beyani107' -> 'Istisnanin Kapsami ve Beyani'
    Ama '3065 sayili Kanun' veya 'Madde 298' gibi yasal ref'leri bozma.
    """
    if not title:
        return title
    # Harf + rakam(lar) ile biten: dipnot
    cleaned = re.sub(r'(?<=[a-zA-ZçğıöşüÇĞİÖŞÜ)ıİ])\d{1,4}$', '', title)
    return cleaned.strip()


def format_content(text):
    """Icerik metnine uygun paragraf kesmeleri ekle"""
    if not text or len(text.strip()) < 10:
        return text.strip()
    
    # Bent isaretleri: a), b), c) gibi
    text = re.sub(r'(?<=[.;:]) +((?:[a-hıçğöşü]\)) )', r'\n\n\1', text)
    
    # Ornek bolumleri
    text = re.sub(r'(?<=[\s.]) *(Örnek\s*\d*\s*:)', r'\n\n\1', text)
    
    # Dipnot: "5 18 Seri No.lu"
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
            
            # Yeni satir mi? (y koordinati degisti)
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
            # Text ve font bilgisi
            text = " ".join(w.get("text", "") for w in line_words).strip()
            
            # Bold mu? (satirdaki bold kelimelerin orani)
            bold_count = sum(1 for w in line_words if "Bold" in w.get("fontname", ""))
            total_count = len(line_words)
            is_bold = bold_count > total_count * 0.5  # %50'den fazla bold ise baslik
            
            # Font boyutu
            avg_size = sum(w.get("size", 11) for w in line_words) / total_count if total_count else 11
            
            if text and not text.isdigit():
                all_lines.append({
                    "text": text,
                    "bold": is_bold,
                    "size": avg_size,
                    "page": page_num + 1
                })
    
    return all_lines


def is_header_line(line):
    """Bu satir bir baslik mi? Bold olmali ve bir baslik kalibina uymali"""
    if not line["bold"]:
        return None
    
    text = line["text"].strip()
    
    # Sayfa basligi filtrele
    if "RESMİ GAZETE" in text.upper() or "RESM" in text:
        return None
    if re.match(r'^\d+ \w+ \d{4}', text):  # Tarih formati
        return None
    if text.startswith("Sayı"):
        return None
    
    # Cok kisa veya cok uzun basliklar
    if len(text) < 2 or len(text) > 250:
        return None
    
    # Baslik kaliplarina uyan mi?
    # Oncelik sirasi: L4 > L3 > L2 > L1 > L0 (spesifikten genele)
    for level_name, pattern in reversed(HEADER_PATTERNS):
        m = pattern.match(text)
        if m:
            return {
                "level": level_name,
                "depth": LEVEL_DEPTH[level_name],
                "id": m.group(1).strip(),
                "title": m.group(2).strip()
            }
    
    return None


def build_hierarchy(lines):
    """Satirlardan hiyerarsi olustur"""
    root = []
    stack = []  # (depth, node) tuples
    last_content_target = None  # Icerik eklenmesi gereken son node
    
    for line in lines:
        text = line["text"].strip()
        
        # Sayfa basligini atla
        if "RESMİ GAZETE" in text.upper() or "RESM" in text:
            continue
        if re.match(r'^\d+ \w+ \d{4}', text):
            continue
        if text.startswith("Sayı") and len(text) < 20:
            continue
        
        # Baslik mi?
        header = is_header_line(line)
        
        if header:
            node = {
                "id": header["id"],
                "title": clean_footnote_from_title(header["title"]),
                "content": "",
                "sub": []
            }
            
            depth = header["depth"]
            
            # Stack'i bu derinlige kadar kes
            while stack and stack[-1][0] >= depth:
                stack.pop()
            
            if not stack:
                # Ust seviye
                root.append(node)
            else:
                # Ust ogeye ekle
                parent = stack[-1][1]
                parent["sub"].append(node)
            
            stack.append((depth, node))
            last_content_target = node
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


def count_items(items):
    """Toplam oge sayisini hesapla"""
    total = len(items)
    for item in items:
        if item.get("sub"):
            total += count_items(item["sub"])
    return total


def print_tree(items, depth=0, max_depth=3):
    """Agaci goster (sinirli derinlik)"""
    for item in items:
        prefix = "  " * depth
        uid = item.get("uid", item["id"])
        title = item.get("title", "")[:55]
        sub_count = len(item.get("sub", []))
        has_content = "+" if item.get("content", "").strip() else "-"
        print(f"{prefix}[{has_content}] {uid} | {title} (sub:{sub_count})")
        
        if item.get("sub") and depth < max_depth:
            print_tree(item["sub"], depth + 1, max_depth)


def main():
    print("=" * 70)
    print("KDV Genel Uygulama Tebligi - Gelismis PDF Parser v2")
    print("=" * 70)
    
    # Yedek al
    if os.path.exists(JSON_OUTPUT):
        import shutil
        shutil.copy2(JSON_OUTPUT, BACKUP_PATH)
        print(f"Yedek: {BACKUP_PATH}")
    
    # PDF'i ac
    print(f"\nPDF aciliyor: {PDF_PATH}")
    pdf = pdfplumber.open(PDF_PATH)
    print(f"Toplam sayfa: {len(pdf.pages)}")
    
    # Satirlari cikar
    print("\nSatirlar cikariliyor (font bilgileri ile)...")
    lines = extract_lines_with_style(pdf)
    bold_count = sum(1 for l in lines if l["bold"])
    print(f"Toplam satir: {len(lines)}, Bold (baslik adayi): {bold_count}")
    
    pdf.close()
    
    # Hiyerarsi olustur
    print("\nHiyerarsi olusturuluyor...")
    data = build_hierarchy(lines)
    print(f"Ust seviye bolum: {len(data)}")
    
    # UID ekle
    print("Benzersiz UID'ler ekleniyor...")
    add_uid_recursive(data)
    
    # Icerikleri formatla
    print("Icerikler formatlanyor...")
    format_all_content(data)
    
    # Toplam istatistikler
    total = count_items(data)
    print(f"\nToplam oge sayisi: {total}")
    
    # Agaci goster
    print("\n--- YAPI AGACI (3 seviye) ---")
    print_tree(data, max_depth=2)
    
    # JSON kaydet
    with open(JSON_OUTPUT, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print(f"\nKaydedildi: {JSON_OUTPUT}")
    print("Tamamlandi!")


if __name__ == "__main__":
    main()
