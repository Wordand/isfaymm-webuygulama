
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

    # Sayfa altı dipnotları ve tarihlerini temizle (örn: "21/12/2021-31696")
    text = re.sub(r'\d{2}/\d{2}/\d{4}-\d+', '', text)
    text = re.sub(r'Sayfa \d+ / \d+', '', text)
    
    # İçindekiler kalıntısı (nokta dizileri)
    text = re.sub(r'\.{4,}.*$', '', text, flags=re.MULTILINE)
    
    lines = text.split('\n')
    cleaned_lines = []
    for l in lines:
        ls = l.strip()
        if not ls: continue
        # Agresif sayfa başlığı/footer temizliği
        if "RESMİ GAZETE" in ls.upper() or "SAYFA" in ls.upper(): continue
        # Sadece tarihten oluşan satırlar
        if re.match(r'^\d{2}\.\d{2}\.\d{4}$', ls): continue
        cleaned_lines.append(ls)
    
    if not cleaned_lines: return ""

    formatted_blocks = []
    current_block = []

    for i, line in enumerate(cleaned_lines):
        # Dipnot satırı tespiti: "52 35 Seri No.lu..." veya "(1) ..."
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
            
            # Bloğa eklemeden önce, eğer dipnot ise önceki blok sonundaki referans sayısını sil
            if is_fn and formatted_blocks:
                formatted_blocks[-1] = re.sub(r'(\w)\d{1,2}$', r'\1', formatted_blocks[-1]).strip()
            
            formatted_blocks.append(line)
        else:
            if not current_block:
                current_block.append(line)
            else:
                prev = current_block[-1]
                should_join = False
                # Birleştirme kuralları
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
    
    # Final temizlik
    processed = []
    for b in formatted_blocks:
        # Cümle içi yapışık dipnot numaraları: "yapılır.32" -> "yapılır."
        # Not: Binlik ayraçlarını (.000) bozmamak için sadece 1-2 basamaklıları hedefliyoruz.
        b = re.sub(r'([\.])(\d{1,2})(\s|$)', r'\1\3', b)
        # Kelimeye yapışık dipnotlar: "şirketleri,32" -> "şirketleri,"
        b = re.sub(r'([,])(\d{1,2})(\s|$)', r'\1\3', b)
        # Fazla boşluklar
        if "<!-- TABLE_START -->" not in b:
            b = re.sub(r' +', ' ', b)
        processed.append(b.strip())

    return "\n\n".join(processed)

def is_toc_line(text):
    return bool(re.search(r'\.{4,}\s*\d*$', text))

def clean_title(title):
    # Başlık sonundaki dipnot numaralarını sil (örn: "Kapsam32")
    t = re.sub(r'([a-zA-ZüğışçöÜĞİŞÇÖ])\d+$', r'\1', title)
    t = re.sub(r'\s+', ' ', t).strip()
    # Başlık sonundaki fazlalık noktaları temizle
    while t.endswith("."): t = t[:-1].strip()
    return t

def is_roman_header(text):
    if is_toc_line(text): return None, None
    # Support "I.", "I-", "I "
    m = re.match(r'^([XVI]+)\s*[\.\-\–\s]\s*(.*)$', text)
    if m:
        roman = m.group(1)
        title = m.group(2).strip()
        if roman in ROMAN_NUMERALS and len(title) > 3 and title[0].isupper():
            if len(title) > 150: return None, None 
            return roman, clean_title(title)
    return None, None

def is_kn_header(text):
    if is_toc_line(text): return None, None
    m = re.match(r'^([A-ZÇĞİÖŞÜ])\s*[\.\-\–]\s*(.*)$', text)
    if m:
        letter = m.group(1)
        title = m.group(2).strip()
        if not title: return None, None
        if len(letter) != 1: return None, None
        if title.startswith(("Ş.", "Şti", "Ltd", "A.Ş", "A Ş")): return None, None
        if title.endswith(".") and len(title) > 100: return None, None 
        if not title[0].isupper(): return None, None
        if len(title) < 3: return None, None
        if "TL" in title or "KDV" in title: return None, None
        
        low_title = tr_lower(title)
        excluded_letters = ["yürürlükten kaldırılan", "geçici hükümler", "yürürlük", "nakden", "banka hesabına", "büyükelçiliği", "araçlar, kıymetli maden", "onaylayan"]
        for ex in excluded_letters:
            if ex in low_title: return None, None
        return letter, clean_title(title)
    return None, None

def is_numeric_header(text):
    if is_toc_line(text): return None, None, None
    
    def is_valid_num(n_str):
        parts = n_str.split('.')
        # Para miktarını elemek için: 
        if any(len(p) >= 3 for p in parts): return False 
        return True

    def is_valid_title(t_str):
        if not t_str: return False
        t_str = t_str.strip()
        
        # --- KRİTİK FİLTRELER ---
        if not t_str[0].isupper(): return False # Başlıklar büyük harfle başlamalı
        if t_str.isdigit(): return False # Sadece sayı (70, 90) olamaz
        if len(t_str) < 3: return False
        
        # Bazı başlıklar biraz daha uzun olabilir
        if len(t_str) > 200: return False
        
        if t_str.endswith("dir.") or t_str.endswith("dır.") or t_str.endswith("tır.") or t_str.endswith("tir."): return False
        if t_str.endswith("belirlenmiştir.") or t_str.endswith("yazılmıştır."): return False
        # Eğer çok uzunsa ve nokta ile bitiyorsa muhtemelen paragraftır, başlık değildir.
        if t_str.endswith(".") and len(t_str.split()) > 10: return False 

        low_t = tr_lower(t_str)
        forbidden_phrases = [
            "seri no.lu", "sayılı kanun", "maddesinde", "fıkrasında", "çerçevesinde", 
            "vergilendirme dönemi", "devreden vergi", "iade hakkı", "hesaplanan kdv", 
            "mükellef,", "mükellefin", "tarafından", "dolayısıyla", "gerekmektedir", 
            "bulunmamaktadır", "örneğin", "tablo", "yukarıda", "aşağıda", "tl'lik", 
            "binde", "oranında", "bu tutar", "bu işlemleri", "mart ve nisan", 
            "herhangi bir", "nakden", "banka hesabına"
        ]
        for phrase in forbidden_phrases:
            if phrase in low_t: return False
        
        if t_str.lstrip().startswith(("TL", "Kr", "Bin TL")): return False
        if "TL olarak" in t_str or "TL ile" in t_str or "TL'dir" in t_str: return False

        return True

    clean_t = text.strip()
    
    # Çok seviyeli (örn: 2.1.3.1.2) başlıkları yakalamak için geliştirilmiş regex
    # Durum 1: Ayırıcı var (2.1.3. - Başlık)
    m1 = re.match(r'^(\d+(?:\.\d+){0,5})\s*[\.\-\–]\s*(.*)$', clean_t)
    # Durum 2: Ayırıcı yok (2.1.3.1 Başlık)
    m2 = re.match(r'^(\d+(?:\.\d+){1,5})\s+(.*)$', clean_t)
    
    m = m1 or m2
    if m:
        num_part, title_part = m.group(1), m.group(2)
        # Seviye 1 (noktasız) ise mutlaka ayırıcı olmalı (dipnotları elemeyi garantilemek için)
        if '.' not in num_part and not m1:
            return None, None, None
            
        if is_valid_num(num_part) and is_valid_title(title_part):
            lvl = len(num_part.split('.'))
            return lvl, num_part, clean_title(title_part)

    return None, None, None

def add_uid_recursive(items, parent_uid=""):
    for item in items:
        uid = item.get("id", "none")
        if parent_uid:
            item["uid"] = f"{parent_uid}/{uid}"
        else:
            item["uid"] = uid
            
        if item.get("sub"):
            add_uid_recursive(item["sub"], item["uid"])

def extract_tables_as_html(page):
    try:
        tables = page.extract_tables()
        html_tables = []
        if tables:
            for table in tables:
                # Temizle: Boş satırları ve sütunları ele
                t_clean = []
                for row in table:
                    if any(cell and cell.strip() for cell in row):
                        t_clean.append([ (c or "").replace("\n", " ").strip() for c in row ])
                
                if not t_clean: continue
                
                # Sütunları kontrol et (tamamen boş sütun var mı?)
                col_mask = [any(row[col] for row in t_clean) for col in range(len(t_clean[0]))]
                t_final = [[row[col] for col in range(len(row)) if col_mask[col]] for row in t_clean]

                html = '\n<!-- TABLE_START -->\n<div class="table-responsive my-3 shadow-sm border rounded"><table class="table table-bordered table-striped table-hover table-sm mb-0" style="font-size: 0.9em;">'
                if len(t_final) > 0:
                    html += '<thead class="table-light"><tr>'
                    for cell in t_final[0]: html += f'<th scope="col" class="fw-bold text-center align-middle">{cell}</th>'
                    html += '</tr></thead><tbody>'
                    for row in t_final[1:]:
                        html += '<tr>'
                        for cell in row: html += f'<td class="align-middle">{cell}</td>'
                        html += '</tr>'
                    html += '</tbody></table></div>\n<!-- TABLE_END -->\n'
                    html_tables.append(html)
        return html_tables
    except Exception as e:
        print(f"Tablo hatası: {e}")
        return []

def parse_pdf():
    print(f"--- ANALİZ BAŞLIYOR MASTER V10 (Multi-line Headers): {PDF_PATH} ---")
    data_structure = []
    stack = [] 
    current_content = []

    with pdfplumber.open(PDF_PATH) as pdf:
        total_pages = len(pdf.pages)
        print(f"Toplam Sayfa: {total_pages}")
        
        for i, page in enumerate(pdf.pages):
            if i % 20 == 0: print(f"İşlenen Sayfa: {i+1}...")
            
            page_tables_html = extract_tables_as_html(page)
            text = page.extract_text()
            if not text: continue
            
            lines = text.split('\n')
            line_idx = 0
            while line_idx < len(lines):
                line = lines[line_idx].strip()
                line_idx += 1
                
                if not line or len(line) < 3: continue
                if "RESMİ GAZETE" in line or re.match(r'^\d+\s+[A-Z][a-z]+', line): continue

                # 1. ROMAN HEADER
                roman, r_title = is_roman_header(line)
                if roman:
                    if stack and current_content:
                         stack[-1][1]["content"] += "\n" + "\n".join(current_content)
                         current_content = []
                    stack = [] 
                    node = {"id": roman, "title": r_title, "content": "", "sub": [], "type": "roman", "page": i+1}
                    data_structure.append(node)
                    stack.append((0, node))
                    continue

                # 2. LETTER HEADER
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

                # 3. NUMERIC HEADER (Multiple Levels)
                lvl, num, n_title = is_numeric_header(line)
                if lvl:
                    # Look ahead for title continuation
                    while line_idx < len(lines):
                        next_line = lines[line_idx].strip()
                        if not next_line: 
                            line_idx += 1
                            continue
                        
                        # Stop if it's another header or clearly separate
                        if is_roman_header(next_line)[0] or is_kn_header(next_line)[0] or is_numeric_header(next_line)[0]:
                            break
                        
                        # Exclusion list for title continuation:
                        # 1. Starts with list marker
                        # 2. Ends with colon
                        # 3. Too long as a continuation
                        # 4. Starts with lowercase (titles rarely continue from lowercase unless it's a sentence)
                        
                        if re.match(r'^(\-|\d+\.|[a-zçğıöşü]\)|•|\*)', next_line): break
                        if next_line.endswith(":") or next_line.endswith(";"): break
                        
                        # Heuristic: Title continuations usually start with uppercase
                        if next_line[0].islower() and len(n_title) > 20: break

                        if len(next_line) < 70 and not next_line.endswith("."):
                            n_title += " " + next_line
                            line_idx += 1
                        elif len(next_line) < 35: 
                            n_title += " " + next_line
                            line_idx += 1
                        else:
                            break
                    
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
            
            if page_tables_html: current_content.extend(page_tables_html)

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
    
    output_dir = os.path.dirname(JSON_OUTPUT)
    if output_dir: os.makedirs(output_dir, exist_ok=True)
    with open(JSON_OUTPUT, 'w', encoding='utf-8') as f:
        json.dump(data_structure, f, ensure_ascii=False, indent=2)
    print(f"BAŞARILI: Veri kaydedildi -> {JSON_OUTPUT}")

if __name__ == "__main__":
    parse_pdf()
