import json
import re
import sys
from pathlib import Path

# Add scratch to sys.path to import integrate_missing_summaries
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

def rebuild():
    # 1. Read clean ozelgeler_88_yeni.txt
    txt_path = ROOT / "services" / "ocr_text" / "ozelgeler_88_yeni.txt"
    if not txt_path.exists():
        print("Error: ozelgeler_88_yeni.txt not found!")
        sys.exit(1)
        
    print("Reading ozelgeler_88_yeni.txt...")
    raw = txt_path.read_text(encoding="utf-8").strip()
    
    # Standardize array concatenation
    raw_combined = '[' + raw.lstrip('[').rstrip(']').replace(']\n[', ',').replace(']\r\n[', ',') + ']'
    try:
        data = json.loads(raw_combined)
        print(f"Loaded {len(data)} items from text file.")
    except Exception as e:
        print(f"JSON Parse Error: {e}")
        sys.exit(1)
        
    # 2. Deduplicate based on ozelge_no or konu
    seen = set()
    unique_items = []
    removed_incorrect = False
    
    for item in data:
        no = (item.get("ozelge_no") or "").strip().lower()
        if "kv-2011-1-32/a-11" in no:
            removed_incorrect = True
            continue
            
        key = no if no else (item.get("konu") or "").strip().lower()
        if key not in seen:
            seen.add(key)
            unique_items.append(item)
            
    print(f"Unique items after deduplication: {len(unique_items)}")
    print(f"Removed incorrect/phantom item: {removed_incorrect}")
    
    # 3. Load the 8 missing items from integrate_missing_summaries
    from scratch.integrate_missing_summaries import missing_items
    print(f"Loaded {len(missing_items)} missing items from scratch.integrate_missing_summaries.")
    
    # 4. Combine
    full_88_items = unique_items + missing_items
    print(f"Total items in combined list: {len(full_88_items)}")
    
    if len(full_88_items) != 88:
        print(f"Warning: Expected exactly 88 items, but got {len(full_88_items)}")
        
    # 5. Save ozelgeler_yeni.json with correct encoding
    out_path = ROOT / "static" / "data" / "ozelgeler_yeni.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    
    out_path.write_text(json.dumps(full_88_items, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Successfully wrote clean data to: {out_path}")

if __name__ == "__main__":
    rebuild()
