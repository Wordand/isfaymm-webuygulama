
import pdfplumber
import json
import re
import os

# --- AYARLAR ---
PDF_PATH = "kdvtebligi.pdf"
JSON_OUTPUT = "static/data/kdv_tebligi.json" 

# --- SABİTLER ---
ROMAN_NUMERALS = ["I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X", "XI", "XII", "XIII", "XIV", "XV", "XVI", "XVII", "XVIII", "XIX", "XX"]

def tr_lower(text):
    if not text: return ""
    return text.replace('İ', 'i').replace('I', 'ı').replace('Ğ', 'ğ').replace('Ü', 'ü').replace('Ş', 'ş').replace('Ö', 'ö').replace('Ç', 'ç').lower()

def clean_text(text):
    if not text: return ""
    if "<!-- TABLE_START -->" in text: return text 

    # Sayfa altı dipnotları ve tarihlerini temizle
    text = re.sub(r'\d{2}/\d{2}/\d{4}-\d+', '', text)
    text = re.sub(r'Sayfa \d+ / \d+', '', text)
    text = re.sub(r'\.{4,}.*$', '', text, flags=re.MULTILINE)
    
    lines = text.split('\n')
    cleaned_lines = []
    for l in lines:
        ls = l.strip()
        if not ls: continue
        if "RESMİ GAZETE" in ls.upper() or "SAYFA" in ls.upper(): continue
        if re.match(r'^\d{2}\.\d{2}\.\d{4}$', ls): continue
        cleaned_lines.append(ls)
    
    if not cleaned_lines: return ""

    formatted_blocks = []
    current_block = []

    for i, line in enumerate(cleaned_lines):
        # Dipnot tespiti
        is_fn = re.match(r'^\d+\s+\d+\s+Seri No', line) or \
                re.match(r'^\d+\s+Seri No', line) or \
                (line.startswith("(") and any(x in line for x in ["Tebliğ", "Değişik", "Yürürlük"]))
        
        is_list = re.match(r'^(\-|\d+\.|[a-zçğıöşü]\)|•|\*)\s', line, re.IGNORECASE)
        if is_list and re.match(r'^\d+\.\d{3}', line): is_list = False

        is_ex = line.upper().startswith("ÖRNEK")

        if is_list or is_ex or is_fn:
            if current_block:
                formatted_blocks.append(" ".join(current_block))
                current_block = []
            
            if is_fn and formatted_blocks:
                formatted_blocks[-1] = re.sub(r'(\w)\d{1,2}$', r'\1', formatted_blocks[-1]).strip()
            
            current_block.append(line)
        else:
            if not current_block:
                current_block.append(line)
            else:
                prev = current_block[-1]
                should_join = False
                if not prev.endswith(('.', ':', ';', '!', '?')): should_join = True
                elif line[0].islower(): should_join = True
                elif line.split()[0].lower() in ["ve", "veya", "ile", "da", "de"]: should_join = True
                
                if should_join:
                    current_block.append(line)
                else:
                    formatted_blocks.append(" ".join(current_block))
                    current_block = [line]
    
    if current_block:
        formatted_blocks.append(" ".join(current_block))
    
    processed = []
    for b in formatted_blocks:
        b = re.sub(r'([\.])(\d{1,2})(\s|$)', r'\1\3', b)
        b = re.sub(r'([,])(\d{1,2})(\s|$)', r'\1\3', b)
        if "<!-- TABLE_START -->" not in b:
            b = re.sub(r' +', ' ', b)
        processed.append(b.strip())

    return "\n\n".join(processed)

def is_toc_line(text):
    return bool(re.search(r'\.{4,}\s*\d*$', text))

def clean_title(title):
    # Harfe yapışık rakamları/dipnotları temizle
    t = re.sub(r'([a-zA-ZüğışçöÜĞİŞÇÖ])\d+', r'\1', title)
    # Parantez içindeki dipnotları temizle (604) veya (609 610)
    t = re.sub(r'\([\d\s,]+\)', '', t)
    # Satır sonundaki rakam ve virgülleri temizle
    t = re.sub(r'(\s+|,)[\d\s,]+$', '', t)
    t = re.sub(r'\s+', ' ', t).strip()
    while t.endswith("."): t = t[:-1].strip()
    return t

def is_roman_header(text):
    if is_toc_line(text): return None, None
    m = re.match(r'^([XVI]+)\s*[\.\-\–\s]\s*(.*)$', text)
    if m:
        roman = m.group(1)
        title = m.group(2).strip()
        if roman in ROMAN_NUMERALS and len(title) > 3 and title[0].isupper():
            if len(title) > 250: return None, None 
            return roman, clean_title(title)
    return None, None

def is_kn_header(text):
    if is_toc_line(text): return None, None
    # Support "A.", "A-", and also "A1.", "A3596." (Letter + index + optional footnote digits)
    # Using non-greedy index to prefer single digit as index unless clarified
    m = re.match(r'^([A-ZÇĞİÖŞÜ][0-9]{1,2}?)(\d*)\s*[\.\-\–]\s*(.*)$', text)
    if not m:
        # Fallback for single letters without trailing numbers (A., B.)
        m = re.match(r'^([A-ZÇĞİÖŞÜ])\s*[\.\-\–]\s*(.*)$', text)
    
    if m:
        groups = m.groups()
        if len(groups) == 3: # Case with optional digits
            letter = groups[0] # A1, A2, A3 etc.
            title = groups[2].strip()
        else:
            letter = groups[0] # A, B, C etc.
            title = groups[1].strip()
            
        if not title: return None, None
        if title.startswith(("Ş.", "Şti", "Ltd", "A.Ş", "A Ş")): return None, None
        if title.endswith(".") and len(title) > 150: return None, None 
        if not title[0].isupper(): return None, None
        if len(title) < 3: return None, None
        
        low_title = tr_lower(title)
        excluded_letters = ["yürürlükten kaldırılan", "geçici hükümler", "yürürlük"]
        for ex in excluded_letters:
            if ex in low_title: return None, None
        return letter, clean_title(title)
    return None, None

def is_numeric_header(text):
    if is_toc_line(text): return None, None, None
    
    def is_valid_num(n_str):
        parts = n_str.split('.')
        if any(len(p) >= 3 for p in parts): return False 
        return True

    def is_valid_title(t_str):
        if not t_str: return False
        t_str = t_str.strip()
        if not t_str[0].isupper(): return False 
        if t_str.isdigit(): return False 
        if len(t_str) < 3: return False
        if len(t_str) > 250: return False
        
        # Başlıklar genelde dir/dır ile bitmez (Cümleleri elemek için)
        
        if t_str.endswith("dir.") or t_str.endswith("dır.") or t_str.endswith("tır.") or t_str.endswith("tir."): return False
        if t_str.endswith("belirlenmiştir.") or t_str.endswith("yazılmıştır."): return False

        low_t = tr_lower(t_str)
        forbidden_phrases = [
            "seri no.lu", "sayılı kanun", "maddesinde", "fıkrasında", 
            "gerekmektedir", "bulunmamaktadır", "örneğin", "tablo", 
            "yukarıda", "aşağıda", "binde", "bu tutar", "bu işlemleri", "mart ve nisan", 
            "herhangi bir", "vergilendirme döneminde", 
            "tl dir", "tl'dir", "tutarında", "hesaplanan kdv"
        ]
        for phrase in forbidden_phrases:
            if phrase in ["binde", "tablo", "yukarıda", "aşağıda"]:
                if re.search(r'\b' + re.escape(phrase) + r'\b', low_t): 
                    return False
            elif phrase in low_t: 
                return False
        
        # Eğer cümle 'mükellef' ile başlayıp nokta ile bitiyorsa başlık değildir
        if low_t.startswith("mükellef") and t_str.endswith("."): return False

        if t_str.lstrip().startswith(("TL", "Kr", "Bin TL")): return False
        if "TL olarak" in t_str or "TL ile" in t_str or "TL'dir" in t_str: return False
        return True

    clean_t = text.strip()
    m_ocr = re.match(r'^([\d\.lI]+)([\s\.\-\–].*)', clean_t)
    if m_ocr:
        num_part = m_ocr.group(1)
        if any(c.isdigit() for c in num_part) and any(c in 'lI' for c in num_part):
            normalized_num = num_part.replace('l', '1').replace('I', '1')
            clean_t = normalized_num + m_ocr.group(2)

    m1 = re.match(r'^(\d+(?:\.\d+){0,5})\s*[\.\-\–]\s*(.*)$', clean_t)
    m2 = re.match(r'^(\d+(?:\.\d+){1,5})\s+(.*)$', clean_t)
    m = m1 or m2
    if m:
        num_part, title_part = m.group(1), m.group(2)
        if is_valid_num(num_part) and is_valid_title(title_part):
            clean_num = num_part.rstrip('.')
            lvl = len(clean_num.split('.'))
            return lvl, clean_num, clean_title(title_part)
    return None, None, None

def add_uid_recursive(items, parent_uid=""):
    for item in items:
        uid = str(item.get("id", "none"))
        if parent_uid:
            item["uid"] = f"{parent_uid}/{uid}"
        else:
            item["uid"] = uid
        if item.get("sub"):
            add_uid_recursive(item["sub"], item["uid"])

def extract_tables_with_coords(page):
    try:
        tables = page.find_tables()
        results = []
        for table in tables:
            bbox = table.bbox # (x0, top, x1, bottom)
            data = table.extract()
            t_clean = []
            for row in data:
                if any(cell and cell.strip() for cell in row):
                    t_clean.append([ (c or "").replace("\n", " ").strip() for c in row ])
            if not t_clean: continue
            
            html = '\n<!-- TABLE_START -->\n<div class="table-responsive my-3 shadow-sm border rounded"><table class="table table-bordered table-striped table-hover table-sm mb-0" style="font-size: 0.9em;">'
            if len(t_clean) > 0:
                html += '<thead class="table-light"><tr>'
                for cell in t_clean[0]: html += f'<th scope="col" class="fw-bold text-center align-middle">{cell}</th>'
                html += '</tr></thead><tbody>'
                for row in t_clean[1:]:
                    html += '<tr>'
                    for cell in row: html += f'<td class="align-middle">{cell}</td>'
                    html += '</tr>'
                html += '</tbody></table></div>\n<!-- TABLE_END -->\n'
                results.append({"html": html, "top": bbox[1], "bbox": bbox})
        return results
    except:
        return []

def parse_pdf():
    print(f"--- ANALİZ BAŞLIYOR MASTER V11 (Coordinate Tables): {PDF_PATH} ---")
    data_structure = []
    stack = [] 
    current_content = []
    parsing_finished = False

    with pdfplumber.open(PDF_PATH) as pdf:
        total_pages = len(pdf.pages)
        print(f"Toplam Sayfa: {total_pages}")
        
        for i, page in enumerate(pdf.pages):
            if parsing_finished: break
            if i % 20 == 0: print(f"İşlenen Sayfa: {i+1}...")
            
            # Tabloları ve metinleri koordinatlarıyla topla
            tables_info = extract_tables_with_coords(page)
            text_line_objs = page.extract_text_lines()
            
            combined_elements = []
            for t in tables_info:
                combined_elements.append({"type": "table", "content": t["html"], "top": t["top"]})
            
            for l_obj in text_line_objs:
                # Eğer satır bir tablonun içindeyse atla
                l_mid = (l_obj["top"] + l_obj["bottom"]) / 2
                in_table = False
                for t in tables_info:
                    tb = t["bbox"]
                    if tb[1] - 1 <= l_mid <= tb[3] + 1:
                        in_table = True
                        break
                if not in_table:
                    combined_elements.append({"type": "text", "content": l_obj["text"].strip(), "top": l_obj["top"]})
            
            # Dikey sıraya göre diz
            combined_elements.sort(key=lambda x: x["top"])
            lines = [item["content"] for item in combined_elements]
            
            line_idx = 0
            while line_idx < len(lines):
                line = lines[line_idx].strip()
                line_idx += 1
                if not line or len(line) < 3: continue
                
                # Tablo ise direkt ekle ve geç
                if "<!-- TABLE_START -->" in line:
                    current_content.append(line)
                    continue

                if "RESMİ GAZETE" in line: continue
                if re.match(r'^\d{1,2}\s+(Ocak|Şubat|Mart|Nisan|Mayıs|Haziran|Temmuz|Ağustos|Eylül|Ekim|Kasım|Aralık)\s+\d{4}', line, re.IGNORECASE): continue

                roman, r_title = is_roman_header(line)
                kn_letter, kn_title = is_kn_header(line)
                num_lvl, num_str, num_title = is_numeric_header(line)

                # DURDURMA NOKTASI: Gereksiz son bölümler
                should_stop = False
                if kn_letter == "C" and "YÜRÜRLÜKTEN KALDIRILAN" in kn_title.upper():
                    should_stop = True
                if num_title and ("KDV İADE ALACAĞININ" in num_title.upper() or "KDVİRA" in num_title.upper()):
                    should_stop = True
                
                if should_stop:
                    parsing_finished = True
                    break
                if roman:
                    if stack and current_content:
                         stack[-1][1]["content"] += "\n" + "\n".join(current_content)
                         current_content = []
                    stack = [] 
                    node = {"id": roman, "title": r_title, "content": "", "sub": [], "type": "roman", "page": i+1}
                    data_structure.append(node)
                    stack.append((0, node))
                    continue

                letter, l_title = is_kn_header(line)
                if letter:
                    if stack and current_content:
                         stack[-1][1]["content"] += "\n" + "\n".join(current_content)
                         current_content = []
                    while stack and stack[-1][0] >= 1: stack.pop()
                    if not stack:
                        if data_structure and data_structure[-1]["type"] == "roman":
                            parent = data_structure[-1]
                            stack.append((0, parent))
                        else:
                            parent = {"id": "GİRİŞ", "title": "GENEL HÜKÜMLER", "content": "", "sub": [], "type": "roman", "page": i+1}
                            data_structure.append(parent)
                            stack.append((0, parent))
                    parent = stack[-1][1]
                    node = {"id": letter, "title": l_title, "content": "", "sub": [], "type": "letter", "page": i+1}
                    parent["sub"].append(node)
                    stack.append((1, node))
                    continue

                lvl, num, n_title = is_numeric_header(line)
                if lvl:
                    while line_idx < len(lines):
                        next_line = lines[line_idx].strip()
                        if not next_line: 
                            line_idx += 1
                            continue
                        if "<!-- TABLE_START -->" in next_line: break
                        if is_roman_header(next_line)[0] or is_kn_header(next_line)[0] or is_numeric_header(next_line)[0]: break
                        if re.match(r'^(\-|\d+\.|[a-zçğıöşü]\)|•|\*)', next_line): break
                        if next_line.endswith(":") or next_line.endswith(";"): break
                        if next_line[0].islower() and len(n_title) > 20: break
                        if len(next_line) < 70 and not next_line.endswith("."):
                            n_title += " " + next_line
                            line_idx += 1
                        elif len(next_line) < 35: 
                            n_title += " " + next_line
                            line_idx += 1
                        else: break
                    
                    n_title = clean_title(n_title)
                    target_depth = lvl + 1
                    if stack and current_content:
                        stack[-1][1]["content"] += "\n" + "\n".join(current_content)
                        current_content = []
                    while stack and stack[-1][0] >= target_depth: stack.pop()
                    if stack:
                        parent = stack[-1][1]
                        node = {"id": num, "title": n_title, "content": "", "sub": [], "type": "numeric", "page": i+1}
                        parent["sub"].append(node)
                        stack.append((target_depth, node))
                    else:
                        current_content.append(line)
                    continue

                current_content.append(line)
            
            if stack and current_content:
                 stack[-1][1]["content"] += "\n" + "\n".join(current_content)
                 current_content = []
    
    def clean_node(n):
        if isinstance(n["content"], list): raw_text = "\n".join(n["content"])
        else: raw_text = n["content"]
        parts = re.split(r'(<!-- TABLE_START -->.*?<!-- TABLE_END -->)', raw_text, flags=re.DOTALL)
        final_parts = []
        for p in parts:
            if "<!-- TABLE_START -->" in p: final_parts.append(p)
            else: final_parts.append(clean_text(p))
        n["content"] = "\n".join(final_parts)
        if n["sub"]:
            for s in n["sub"]: clean_node(s)

    for d in data_structure: clean_node(d)
    add_uid_recursive(data_structure)
    with open(JSON_OUTPUT, 'w', encoding='utf-8') as f:
        json.dump(data_structure, f, ensure_ascii=False, indent=2)
    print(f"BAŞARILI: Veri kaydedildi -> {JSON_OUTPUT}")

if __name__ == "__main__":
    parse_pdf()
