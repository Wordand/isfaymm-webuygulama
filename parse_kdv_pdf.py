import pdfplumber
import json
import re
import os

def parse_kdv_tebligi(pdf_path, json_output_path):
    # Regex patterns for different header levels
    # Supports Roman (I., II.), Letters (A., B.), Numbers (1., 2.), and Dot notation (1.1, 1.1.1)
    patterns = [
        ('L1', re.compile(r'^([IVXLCDM]+)\s*-\s*(.*)$')), # Roman - Title (e.g. I - MÜKELLEFİYET)
        ('L1_alt', re.compile(r'^([IVXLCDM]+)\.\s*(.*)$')), # Roman . Title
        ('L2', re.compile(r'^([A-ZÇĞİÖŞÜ])\s*-\s*(.*)$')), # Letter - Title (e.g. A - VERGİNİN KONUSU)
        ('L2_alt', re.compile(r'^([A-ZÇĞİÖŞÜ])\.\s*(.*)$')), # Letter . Title
        ('L5', re.compile(r'^(\d+\.\d+\.\d+)\.?\s*(.*)$')), # 1.1.1
        ('L4', re.compile(r'^(\d+\.\d+)\.?\s*(.*)$')), # 1.1
        ('L3', re.compile(r'^(\d+)\s*-\s*(.*)$')), # 1 - Title
        ('L3_alt', re.compile(r'^(\d+)\.\s*(.*)$')), # 1. Title
    ]

    # Map internal level names to hierarchy depth (0-indexed)
    level_depth = {
        'L1': 0, 'L1_alt': 0,
        'L2': 1, 'L2_alt': 1,
        'L3': 2, 'L3_alt': 2,
        'L4': 3,
        'L5': 4
    }

    data = []
    stack = [] # current active node at each depth

    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if not text: continue
            
            lines = text.split('\n')
            for line in lines:
                line = line.strip()
                if not line or line.isdigit(): continue
                if "RESMİ GAZETE" in line.upper(): continue

                # Clean up dots from TOC lines (e.g. "Title ............ 55")
                line = re.sub(r'\.{3,}.*$', '', line).strip()

                match_found = False
                for level_name, pattern in patterns:
                    m = pattern.match(line)
                    if m:
                        node_id = m.group(1).strip()
                        node_title = m.group(2).strip()
                        depth = level_depth[level_name]
                        
                        node = {
                            "id": node_id,
                            "title": node_title,
                            "depth": depth,
                            "content": "",
                            "sub": []
                        }
                        
                        # Adjust stack for current depth
                        stack = stack[:depth]
                        
                        if depth == 0:
                            data.append(node)
                        elif stack:
                            # Add specifically as sub of the parent in the stack
                            stack[-1]["sub"].append(node)
                        else:
                            # Orphaned node (faulty hierarchy), treat as root if it's L2 but no L1
                            data.append(node)
                        
                        stack.append(node)
                        match_found = True
                        break
                
                if not match_found and stack:
                    stack[-1]["content"] += line + " "

    # Clean up contents and remove duplicates/jargon
    processed_data = []
    seen_ids = set()

    def clean_and_collect(items, target_list):
        for item in items:
            # Simple deduplication by (id, title)
            key = f"{item['id']}|{item['title']}"
            if key in seen_ids: continue
            seen_ids.add(key)
            
            item["content"] = item["content"].strip()
            # If title is all caps and very long, it might be junk
            if len(item["title"]) > 200: continue
            
            new_item = {
                "id": item["id"],
                "title": item["title"],
                "content": item["content"],
                "sub": []
            }
            target_list.append(new_item)
            if item["sub"]:
                clean_and_collect(item["sub"], new_item["sub"])

    clean_and_collect(data, processed_data)

    with open(json_output_path, 'w', encoding='utf-8') as f:
        json.dump(processed_data, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    parse_kdv_tebligi("kdvtebligi.pdf", "static/data/kdv_tebligi.json")
    print("Parsing complete.")
