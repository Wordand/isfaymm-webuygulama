import xml.etree.ElementTree as ET
import re
from datetime import datetime
import json

def parse_float(text):
    if not text:
        return 0.0
    try:
        # Convert Turkish format (1.234,56) to float
        if "," in text and "." in text:
             # e.g. 1.234,56 -> 1234.56
             return float(text.replace(".", "").replace(",", "."))
        elif "," in text:
             # e.g. 1234,56 -> 1234.56
             return float(text.replace(",", "."))
        return float(text)
    except ValueError:
        return 0.0

def get_text(element, tag_name, default=""):
    found = element.find(tag_name)
    if found is not None and found.text:
        return found.text.strip()
    return default

def get_recursive_text(element, tag_identifiers):
    """
    Searches for a tag recursively that matches any of the identifiers.
    """
    for tag in tag_identifiers:
        found = element.find(f".//{tag}")
        if found is not None and found.text:
            return found.text.strip()
    return None

def extract_general_info(root):
    genel = root.find("genelBilgiler")
    if genel is None:
        return {}
    
    idari = genel.find("idari")
    mukellef = genel.find("mukellef")
    
    info = {
        "vergi_kimlik_no": "",
        "unvan": "",
        "donem": "",
        "yil": "",
        "ay": ""
    }
    
    if idari is not None:
        yil = get_text(idari, "yil")
        ay = get_text(idari, "ay")
        donem_tip = get_text(idari, "donemTip")
        if ay and yil:
            info["donem"] = f"{ay} / {yil}"
        elif yil:
            info["donem"] = yil
        info["yil"] = yil
        info["ay"] = ay

    if mukellef is not None:
        vkn = get_text(mukellef, "vergiNo") or get_text(mukellef, "vergiKimlikNo")
        tckn = get_text(mukellef, "tcKimlikNo")
        soyadi = get_text(mukellef, "soyad")
        adi = get_text(mukellef, "ad")
        unvan_tic = get_text(mukellef, "ticaretUnvani") or get_text(mukellef, "unvan")
        
        info["vergi_kimlik_no"] = vkn if vkn else tckn
        
        if unvan_tic:
            info["unvan"] = unvan_tic
        else:
            info["unvan"] = f"{adi} {soyadi}".strip()
            
    return info

def parse_kdv_xml(root):
    info = extract_general_info(root)
    kdv_node = root.find("kdv1") or root.find("kdv") 
    # Try generic search if kdv1 not found directly (namespace issues sometimes)
    if kdv_node is None:
        # Search for any tag starting with kdv
        for child in root:
            if "kdv" in child.tag.lower():
                kdv_node = child
                break
    
    if kdv_node is None:
        return {"hata": "KDV verisi bulunamadı (XML yapısı farklı olabilir)."}

    matrah_node = kdv_node.find("matrah")
    veriler = []
    
    # 1. Tevkifat Uygulanmayan İşlemler
    if matrah_node is not None:
        # Strategy: Look for specific sub-lists
        # Common structure: <tevkifatUygulanmayanIslemler><satir>...
        
        # Helper to process a list of transactions
        def process_list(parent_tag, row_tag, type_label):
            parent = matrah_node.find(parent_tag)
            if parent is not None:
                for row in parent.findall(row_tag) or parent.findall("islem"):
                    tur = get_text(row, "turAd") or get_text(row, "tur")
                    matrah = parse_float(get_text(row, "matrah"))
                    vergi = parse_float(get_text(row, "vergi"))
                    if matrah > 0:
                        veriler.append({
                            "alan": f"{tur} - Matrah",
                            "deger": f"{matrah:,.2f}",
                            "tip": "data"
                        })
                        veriler.append({
                            "alan": f"{tur} - Vergi",
                            "deger": f"{vergi:,.2f}",
                            "tip": "data"
                        })

        veriler.append({"alan": "§ TEVKİFAT UYGULANMAYAN İŞLEMLER", "deger": "", "tip": "header"})
        process_list("tevkifatUygulanmayanIslemler", "satir", "Normal")
        process_list("kdvTevkifatUygulanmayanIslemler", "satir", "Normal") # Variasyon

        veriler.append({"alan": "§ KISMİ TEVKİFAT UYGULANAN İŞLEMLER", "deger": "", "tip": "header"})
        process_list("kismiTevkifatUygulananIslemler", "satir", "Kismi")
        
        veriler.append({"alan": "§ DİĞER İŞLEMLER", "deger": "", "tip": "header"})
        process_list("digerIslemler", "satir", "Diger")
        
        # Totals
        toplam_matrah = parse_float(get_text(matrah_node, "toplamMatrah") or get_text(matrah_node, "matrahToplami"))
        veriler.append({"alan": "§ MATRAH TOPLAMI", "deger": "", "tip": "header"})
        veriler.append({"alan": "Matrah Toplamı", "deger": f"{toplam_matrah:,.2f}", "tip": "data"})
        
    # Sonuçlar
    sonuc = kdv_node.find("sonuc")
    if sonuc is not None:
        veriler.append({"alan": "§ SONUÇ", "deger": "", "tip": "header"})
        odenmesi = parse_float(get_text(sonuc, "odenmesiGerekenKDV"))
        if odenmesi > 0:
            veriler.append({"alan": "Bu Dönemde Ödenmesi Gereken Katma Değer Vergisi", "deger": f"{odenmesi:,.2f}", "tip": "data"})
        
        devreden = parse_float(get_text(sonuc, "sonrakiDonemeDevredenKDV"))
        if devreden > 0:
             veriler.append({"alan": "Sonraki Döneme Devreden KDV", "deger": f"{devreden:,.2f}", "tip": "data"})

    return {
        "tur": "kdv",
        "donem": info["donem"],
        "unvan": info["unvan"],
        "vergi_kimlik_no": info["vergi_kimlik_no"],
        "veriler": veriler
    }

def parse_kurumlar_xml(root):
    info = extract_general_info(root)
    mali_tablolar = root.find(".//maliTablolar") # Deep search
    
    if mali_tablolar is None:
        # Fallback for simple structure
        kurumlar = root.find("kurumlar")
        if kurumlar:
            mali_tablolar = kurumlar.find("maliTablolar")

    if mali_tablolar is None:
         return {"hata": "Mali tablolar (Bilanço/Gelir Tablosu) bulunamadı."}

    # --- GELİR TABLOSU ---
    gelir_tablosu = mali_tablolar.find("gelirTablosu")
    gelir_data = []
    
    if gelir_tablosu is not None:
        for kalem in gelir_tablosu.findall("kalem") + gelir_tablosu.findall("toplam"): # Both tags
            kod = kalem.get("kod") or get_text(kalem, "kod")
            ad = kalem.get("ad") or get_text(kalem, "ad") or get_text(kalem, "aciklama")
            
            # Attributes parsing (BDP style often uses attributes 'cari' 'onceki')
            cari = parse_float(kalem.get("cari") or get_text(kalem, "cari"))
            onceki = parse_float(kalem.get("onceki") or get_text(kalem, "onceki"))
            
            if not kod and not ad: continue
            
            gelir_data.append({
                "kod": kod,
                "aciklama": ad,
                "cari_donem": cari,
                "onceki_donem": onceki
            })

    # --- BİLANÇO ---
    bilanco = mali_tablolar.find("bilanco")
    bilanco_data = {"aktif": [], "pasif": []}
    
    if bilanco is not None:
        for side in ["aktif", "pasif"]:
            side_node = bilanco.find(side)
            if side_node is not None:
                for item in side_node.findall("kalem") + side_node.findall("grup") + side_node.findall("toplam") + side_node.findall("genelToplam"):
                    kod = item.get("kod")
                    ad = item.get("ad")
                    
                    # Usually bilanco items in XML are just text value if simplified, or attributes
                    # Try text content as value first
                    val_text = item.text
                    cari = parse_float(val_text) if val_text and val_text.strip() else 0.0
                    
                    # If Attribute based
                    if cari == 0.0 and item.get("tutar"):
                        cari = parse_float(item.get("tutar"))
                        
                    desc = ad if ad else (f"Kalem {kod}" if kod else "Bilinmeyen")
                    
                    bilanco_data[side].append({
                        "Kod": kod,
                        "Açıklama": desc,
                        "Cari Dönem": cari,
                        "Önceki Dönem": 0.0 # XML usually has current only for Bilanco or separate years? Assuming current for now.
                    })

    return {
        "tur": "bilanco_gelir", # Combined return
        "unvan": info["unvan"],
        "donem": info["donem"],
        "vergi_kimlik_no": info["vergi_kimlik_no"],
        "gelir_tablosu": gelir_data,
        "bilanco": bilanco_data
    }

def parse_xml_file(file_path):
    try:
        tree = ET.parse(file_path)
        root = tree.getroot()
        
        # Identification Strategy
        root_tag = root.tag.lower()
        
        is_beyanname = "beyanname" in root_tag
        is_kdv = False
        is_kurumlar = False
        
        # Check children
        for child in root:
            tag = child.tag.lower()
            if "kdv" in tag:
                is_kdv = True
            if "kurumlar" in tag or "geçici" in tag: # Kurumlar or Gecici usually have income data
                is_kurumlar = True
                
        # Attributes check
        xsi_loc = root.get("{http://www.w3.org/2001/XMLSchema-instance}noNamespaceSchemaLocation") or ""
        if "kdv" in xsi_loc.lower():
            is_kdv = True
        if "kurum" in xsi_loc.lower():
            is_kurumlar = True

        if is_kdv:
            return parse_kdv_xml(root)
        elif is_kurumlar:
            return parse_kurumlar_xml(root)
        else:
            return {"hata": "XML türü belirlenemedi veya desteklenmiyor (Sadece KDV ve Kurumlar)."}

    except ET.ParseError as e:
        return {"hata": f"XML Okuma Hatası: {e}"}
    except Exception as e:
        return {"hata": f"Beklenmeyen Hata: {e}"}
