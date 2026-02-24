
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

    text = re.sub(r'\.{4,}.*$', '', text)
    lines = text.split('\n')
    cleaned_lines = [re.sub(r'\s+', ' ', l).strip() for l in lines if l.strip()]
    
    formatted_blocks = []
    current_block = []

    for line in cleaned_lines:
        is_list_item = re.search(r'^(\-|•|\*|\d+\.|[a-zçğıöşü]\))\s', line, re.IGNORECASE)
        # Hata önleyici: 20.000 gibi sayılar liste değildir.
        if is_list_item and re.search(r'^\d+\.\d{3}', line): is_list_item = False

        is_example = line.startswith("Örnek") or line.startswith("ÖRNEK")
        is_footnote = line.startswith("(") and ("Tebliğ" in line or "Değişik" in line or "Yürürlük" in line)

        if is_list_item or is_example or is_footnote:
            if current_block: formatted_blocks.append(" ".join(current_block))
            current_block = []
            formatted_blocks.append(line)
        else:
            if not current_block: current_block.append(line)
            else:
                last_line_part = current_block[-1]
                if line[0].isupper() and (last_line_part.endswith('.') or last_line_part.endswith(':')):
                    formatted_blocks.append(" ".join(current_block))
                    current_block = [line]
                else: current_block.append(line)
    
    if current_block: formatted_blocks.append(" ".join(current_block))
    return "\n\n".join(formatted_blocks)

def is_toc_line(text):
    return bool(re.search(r'\.{4,}\s*\d*$', text))

def clean_title(title):
    t = re.sub(r'\s+', ' ', title).strip()
    return re.sub(r'(?<=[a-zA-ZüğışçöÜĞİŞÇÖ])\d+$', '', t).strip()

def is_roman_header(text):
    if is_toc_line(text): return None, None
    m = re.match(r'^([XVI]+)\s*[\.\-\–]\s*(.*)$', text)
    if m:
        roman = m.group(1)
        title = m.group(2)
        if roman in ROMAN_NUMERALS and len(title) > 3 and title.strip()[0].isupper():
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
        if t_str.isdigit(): return False # Sadece sayı (70, 90) olamaz
        if len(t_str) < 3: return False
        
        # Bazı başlıklar biraz daha uzun olabilir (örn. 25/12/2003 tarihli... gibi)
        if len(t_str) > 120: return False
        
        if t_str.endswith("dir.") or t_str.endswith("dır.") or t_str.endswith("tır.") or t_str.endswith("tir."): return False
        if t_str.endswith("belirlenmiştir.") or t_str.endswith("yazılmıştır."): return False
        # Eğer çok uzunsa ve nokta ile bitiyorsa muhtemelen paragraftır, başlık değildir.
        if t_str.endswith(".") and len(t_str.split()) > 6: return False 

        low_t = tr_lower(t_str)
        forbidden_phrases = ["vergilendirme dönemi", "devreden vergi", "iade hakkı", "hesaplanan kdv", "mükellef,", "mükellefin", "tarafından", "dolayısıyla", "gerekmektedir", "bulunmamaktadır", "örneğin", "tablo", "yukarıda", "aşağıda", "tl'lik", "binde", "oranında", "bu tutar", "bu işlemleri", "mart ve nisan", "herhangi bir", "nakden", "banka hesabına"]
        for phrase in forbidden_phrases:
            if phrase in low_t: return False
        
        if t_str.lstrip().startswith(("TL", "Kr", "Bin TL")): return False
        if "TL olarak" in t_str or "TL ile" in t_str or "TL'dir" in t_str: return False

        return True

    clean_t = text.strip()
    
    # Çok seviyeli (örn: 2.1.3.1.2) başlıkları yakalamak için geliştirilmiş regex
    # En uzun eşleşmeyi yakalamak için \d+(?:\.\d+)* kullanıyoruz
    m = re.match(r'^(\d+(?:\.\d+){0,5})\s*[\.\-\–]?\s*(.*)$', clean_t)
    if m:
        num_part, title_part = m.group(1), m.group(2)
        if is_valid_num(num_part) and is_valid_title(title_part):
            lvl = len(num_part.split('.'))
            return lvl, num_part, clean_title(title_part)

    return None, None, None

    return None, None, None

def add_uid_recursive(items, parent_uid=""):
    for item in items:
        if parent_uid:
            if parent_uid == "": item["uid"] = item["id"]
            else: item["uid"] = f"{parent_uid}/{item['id']}"
        else: item["uid"] = item["id"]
        if item.get("sub"): add_uid_recursive(item["sub"], item["uid"])

def extract_tables_as_html(page):
    try:
        tables = page.extract_tables()
        html_tables = []
        if tables:
            for table in tables:
                if not table or not any(row for row in table if any(cell and cell.strip() for cell in row)): continue
                html = '\n<!-- TABLE_START -->\n<div class="table-responsive my-3 shadow-sm border rounded"><table class="table table-bordered table-striped table-hover table-sm mb-0" style="font-size: 0.9em;">'
                if len(table) > 0:
                    html += '<thead class="table-light"><tr>'
                    for cell in table[0]: html += f'<th scope="col" class="fw-bold text-center align-middle">{(cell or "").replace("\n", " ").strip()}</th>'
                    html += '</tr></thead><tbody>'
                    for row in table[1:]:
                        if not any(cell and cell.strip() for cell in row): continue
                        html += '<tr>'
                        for cell in row: html += f'<td class="align-middle">{(cell or "").replace("\n", "<br>").strip()}</td>'
                        html += '</tr>'
                    html += '</tbody></table></div>\n<!-- TABLE_END -->\n'
                    html_tables.append(html)
        return html_tables
    except Exception as e:
        print(f"Tablo hatası: {e}")
        return []

def parse_pdf():
    print(f"--- ANALİZ BAŞLIYOR MASTER V9 (Final Fix): {PDF_PATH} ---")
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
            
            for line in lines:
                line = line.strip()
                if not line or len(line) < 3: continue
                if "RESMİ GAZETE" in line or re.match(r'^\d+\s+[A-Z][a-z]+', line): continue

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
