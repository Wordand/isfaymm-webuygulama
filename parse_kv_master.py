
import pdfplumber
import json
import re
import os

# --- AYARLAR ---
PDF_PATH = "kurumlarvergisiteblig.pdf"
JSON_OUTPUT = "static/data/kv_tebligi.json" 

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
    
    # 1. Footnotes Detection & Formatting
    # Regex explanation:
    # Look for digits (\d+) that are:
    # - At the end of the string ($)
    # OR
    # - Following a closing parenthesis `)` possibly with spaces, and avoiding cases where it might be a year (like 2004) or a law number?
    # Actually, in the example: "Bankalara, (Ek ibare: ...-30279)27 finansal kiralama..."
    # The '27' is in the middle, right after the closing paren.
    # We need to find `)` followed by digits, then continue with text.
    
    def format_footnote(match):
        # match group 1: the closing parenthesis part including the parens
        # match group 2: the footnote number
        # match group 3: the rest of the text (if any)
        # Note: We need to be careful not to capture things like (1) as a footnote if it's an item list.
        # But here we are cleaning a *title*.
        
        pre = match.group(1) # e.g. ")" or ")...)"
        num = match.group(2)
        
        # Heuristic: If num length > 3, it's probably not a footnote marker (e.g. year 2004 or law no).
        if len(num) > 3: return match.group(0)
        
        return f'{pre}<sup class="text-secondary fw-normal fst-italic ms-0">{num}</sup>'

    # Pattern: "...)...)27 ..."
    # Find `)` followed optionally by space, then digits, then space or end-of-string or comma/dot
    # We will replace the digits with the <sup> tag.
    # This covers ")...)27" in middle and at end.
    t = re.sub(r'(\))\s*(\d+)', format_footnote, t)
    
    # Also handle trailing digits that might not follow a paren (like "İstisna11")
    # Only if we haven't already processed them (though the above regex needs parens).
    # So we keep the logic for trailing digits if no parens involved.
    # But wait, `format_parens` below might interfere if we do this first? 
    # Let's do footnotes first, then parens formatting.
    
    m_foot_end = re.search(r'(?<=\D)(\d+)$', t) # Digits at end, preceded by non-digit
    if m_foot_end:
        num = m_foot_end.group(1)
        if len(num) < 4:
            # Check if this was already handled by the paren regex? 
            # The paren regex consumes the paren. If the number is at the very end, it would be caught by `)\s*(\d+)`.
            # If the title ends with "Title 11", this catches it.
            # We must be careful not to double replace.
            # Simplest: Just use one pass for "digits after non-digit char".
            # But "Title 2004" is year. "Title 11" is footnote.
            # Let's stick to the specific "after paren" pattern OR "at end" pattern.
            pass # We'll trust the specific regexes.

    # Let's refine the "at end" check to replace ONLY if it wasn't replaced yet (no <sup> tag).
    if not t.endswith('</sup>'):
        def format_trailing(m):
            n = m.group(1)
            if len(n) < 4: return f'<sup class="text-secondary fw-normal fst-italic ms-1">{n}</sup>'
            return m.group(0)
        t = re.sub(r'(?<=[a-zA-ZüğışçöÜĞİŞÇÖ\.\,])\s*(\d+)$', format_trailing, t)


    # 2. Parenthetical Notes (Değişik yapılar)
    def format_parens(match):
        content = match.group(0)
        # Keywords to identify legal notes
        keywords = ["Değişik", "Mülga", "Yürürlük", "RG", "Resmi Gazete", "Ek ibare", "Ek cümle"]
        if any(kw in content for kw in keywords):
            return f'<span class="fw-normal fst-italic text-muted small">{content}</span>'
        return content

    # Apply formatting to parenthetical blocks
    t = re.sub(r'\([^\)]+\)', format_parens, t)
    
    return t

def is_roman_header(text):
    if is_toc_line(text): return None, None
    m = re.match(r'^([XVI]+)\s*[\.\-\–]\s*(.*)$', text)
    if m:
        roman = m.group(1)
        title = m.group(2).strip()
        
        # --- KESİN FİLTRELER ---
        if ":" in title: return None, None
        if "..." in title: return None, None
        if "/" in title and any(char.isdigit() for char in title): return None, None # Tarih formatları (15/4/2006)
        
        title_lower = title.lower()
        forbidden = ["tasfiye dönemi", "kazanç", "zarar", "döneminde", "ytl", " tl", "tarihi", "avans", "tutarı"]
        if any(f in title_lower for f in forbidden): return None, None
        
        # Roma rakamlı ana başlıklar genelde uzundur veya büyük harftir, ama çok kısa "X. YYY" gibi olabilir.
        # Yine de satırın çoğu küçük harfse şüphelenelim (Örnek metnindeki maddeler gibi)
        uppercase_count = sum(1 for c in title if c.isupper())
        lowercase_count = sum(1 for c in title if c.islower())
        if lowercase_count > uppercase_count and lowercase_count > 5: return None, None

        if roman in ROMAN_NUMERALS and len(title) > 2:
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
        
        # --- YANLIŞ POZİTİFLERİ ENGELLEME ---
        if title.startswith("C."): return None, None # T.C. yakalaması
        if title.startswith("Ş."): return None, None # A.Ş. yakalaması
        if title.startswith("Merkez Bankası"): return None, None
        if title.startswith("Kanun"): return None, None
        
        if ":" in title: return None, None
        if "..." in title: return None, None
        
        low_title = tr_lower(title)
        excluded = [
            "yürürlükten kaldırılan", "geçici hükümler", "yürürlük", "nakden", "banka hesabına", 
            "büyükelçiliği", "araçlar, kıymetli maden", "onaylayan", "tasfiye dönemi", 
            "döneminde", "kazanç", "zarar", "tutarı", "vergisi", "tebliği"
        ]
        if any(ex in low_title for ex in excluded): return None, None

        # Şirket unvanı gibi görünenleri ele
        if "şti" in low_title or "ltd" in low_title or "a.ş" in low_title: return None, None

        return letter, clean_title(title)
    return None, None

def is_numeric_header(text):
    if is_toc_line(text): return None, None, None
    
    def is_valid_num(n_str):
        parts = n_str.split('.')
        # 3 haneli ve 500/000 ile biten parça varsa para miktarıdır (22.500)
        # Ama 100. Yıl gibi tarihler veya 3.300. madde olabilir mi? Nadir.
        if any(len(p) == 3 for p in parts if p.isdigit()): return False 
        return True

    def is_valid_title(t_str):
        if not t_str: return False
        t_str = t_str.strip()
        
        # --- NEW Strict Filter ---
        # Başlıklar kesinlikle Büyük Harfle (veya rakamla değil) başlamalıdır.
        # "2 satış:" gibi maddeleri eler.
        if t_str and t_str[0].islower(): return False

        # --- FILTERS ---
        if t_str[0].isdigit(): return False
        if any(s in t_str for s in ['=', '+', 'x ']): return False
        if "TL" in t_str or "YTL" in t_str: return False
        if "Dolar" in t_str or "Euro" in t_str: return False
        if len(t_str) < 3: return False
        if len(t_str) > 300: return False  # Increased limit for long headers with notes
        if "..." in t_str: return False
        # if ":" in t_str: return False  # Removed to support headers with colons in notes (e.g. RG-...)

        low_t = tr_lower(t_str)
        forbidden_phrases = [
            "vergilendirme dönemi", "devreden vergi", "iade hakkı", "hesaplanan kdv", 
            "mükellef,", "mükellefin", "dolayısıyla", 
            "örneğin", "tablo", "yukarıda", "aşağıda", "binde", 
            "bu tutar", "bu işlemleri", "herhangi bir", "nakden", 
            "banka hesabına", "tasfiye dönemi",
            "yasal düzenleme", "kapsam ve", "örnek", "varsayılarak"
        ]
        if any(phrase in low_t for phrase in forbidden_phrases): return False
        return True

    clean_t = text.strip()
    
    # Regexleri sırayla dene.
    # Allow spaces in numbers: 4 . 1 . 2 -> 4.1.2
    
    # LEVEL 5 CHECK (YENİ) - 4.13.1.4.1 gibi
    # Regex: ^(\d+)\.\d+\.\d+\.\d+\.\d+
    m5 = re.match(r'^(\d+)\s*\.\s*(\d+)\s*\.\s*(\d+)\s*\.\s*(\d+)\s*\.\s*(\d+)\s*[\.\-\–]?\s*(.*)$', clean_t)
    if m5:
        n = f"{m5.group(1)}.{m5.group(2)}.{m5.group(3)}.{m5.group(4)}.{m5.group(5)}"
        t = m5.group(6)
        if is_valid_num(n) and is_valid_title(t): return 5, n, clean_title(t)

    # LEVEL 4 CHECK
    m4 = re.match(r'^(\d+)\s*\.\s*(\d+)\s*\.\s*(\d+)\s*\.\s*(\d+)\s*[\.\-\–]?\s*(.*)$', clean_t)
    if m4:
        n = f"{m4.group(1)}.{m4.group(2)}.{m4.group(3)}.{m4.group(4)}"
        t = m4.group(5)
        if is_valid_num(n) and is_valid_title(t): return 4, n, clean_title(t)

    # LEVEL 3 CHECK
    m3 = re.match(r'^(\d+)\s*\.\s*(\d+)\s*\.\s*(\d+)\s*[\.\-\–]?\s*(.*)$', clean_t)
    if m3:
        n = f"{m3.group(1)}.{m3.group(2)}.{m3.group(3)}"
        t = m3.group(4)
        if re.match(r'^\d+\.\s', t): pass 
        if is_valid_num(n) and is_valid_title(t): return 3, n, clean_title(t)

    # LEVEL 2 CHECK
    m2 = re.match(r'^(\d+)\s*\.\s*(\d+)\s*[\.\-\–]?\s*(.*)$', clean_t)
    if m2:
        n = f"{m2.group(1)}.{m2.group(2)}"
        t = m2.group(3)
        if is_valid_num(n) and is_valid_title(t): return 2, n, clean_title(t)

    # LEVEL 1 CHECK
    m1 = re.match(r'^(\d+)\s*[\.\-\–]\s*(.*)$', clean_t)
    if m1:
        n = m1.group(1)
        t = m1.group(2)
        if is_valid_num(n) and is_valid_title(t): return 1, n, clean_title(t)

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
    print(f"--- KURUMLAR VERGİSİ ANALİZ BAŞLIYOR: {PDF_PATH} ---")
    data_structure = []
    stack = [] 
    current_content = []

    try:
        with pdfplumber.open(PDF_PATH) as pdf:
            total_pages = len(pdf.pages)
            print(f"Toplam Sayfa: {total_pages}")
            
            # last_l1_num = 0 -> Replaced by tracker
            seq_tracker = {1:0, 2:0, 3:0, 4:0, 5:0}

            for i, page in enumerate(pdf.pages):
                if i % 20 == 0: print(f"İşlenen Sayfa: {i+1}...")
                
                page_tables_html = extract_tables_as_html(page)
                text = page.extract_text()
                if not text: continue
                
                # Pre-process text to handle embedded headers
                # Example: "...text. 5.1. Header..." -> "...text.\n5.1. Header..."
                # Look for pattern: sentence ending (.), spaces, then numeric header pattern starting with uppercase
                # SUPPORT UP TO LEVEL 5: (\s*\.\s*\d+){1,4} -> Allow spaces like "4 . 13 . 1"
                text = re.sub(r'(?<=[a-z])\.\s+(\d+(\s*\.\s*\d+){1,4}\.?\s+[A-ZİÖÜŞÇĞ])', r'.\n\1', text)
                
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

                    # 3. SAYISAL (1. , 1.1. , 1.1.2)
                    lvl, num, n_title = is_numeric_header(line)
                    if lvl:
                        # --- SEQUENCE VALIDATION (ALL LEVELS) ---
                        is_valid_sequence = True
                        
                        try:
                            # Extract the last part of the number for the current level
                            # 5.1 -> current_n = 1
                            # 5.1.2 -> current_n = 2
                            parts = num.split('.')
                            if len(parts) >= lvl:
                                current_n = int(parts[lvl-1])
                                
                                # Parent check is implicit by hierarchy, but we tracked last seen numbers
                                # Check against last seen number for THIS level
                                last_n = seq_tracker.get(lvl, 0)
                                
                                if last_n > 0:
                                    if current_n == last_n: 
                                        is_valid_sequence = False # Duplicate (5.1 -> 5.1)
                                    elif current_n < last_n:
                                        # Backward jump
                                        # Strict: if diff > 0 reject.
                                        pass
                                
                                # Logic to reset lower trackers if this is valid
                                if is_valid_sequence:
                                     # Strict backward check
                                     if current_n < last_n and (last_n - current_n > 0): 
                                         is_valid_sequence = False
                                     
                                     if is_valid_sequence:
                                         seq_tracker[lvl] = current_n
                                         # Reset all deeper levels
                                         for l in range(lvl + 1, 6): # Up to 5
                                             seq_tracker[l] = 0
                                         
                        except:
                            pass # allow if parse fails (fallback)

                        if is_valid_sequence:
                            target_depth = lvl + 1
                            if stack and current_content:
                                stack[-1][1]["content"] += "\n" + "\n".join(current_content)
                                current_content = []
                            
                            # Stack yönetimi
                            while stack and stack[-1][0] >= target_depth: stack.pop()
                            
                            if stack:
                                parent = stack[-1][1]
                                node = {"id": num, "title": n_title, "content": "", "sub": [], "type": "numeric", "page": i+1}
                                parent["sub"].append(node)
                                stack.append((target_depth, node))
                                continue
                            else:
                                current_content.append(line)
                                continue
                        else:
                             # Sequence hatası -> Metin olarak ekle
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

    except Exception as e:
        print(f"Bir hata oluştu: {e}")

if __name__ == "__main__":
    parse_pdf()
