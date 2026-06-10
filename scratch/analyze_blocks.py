import re
import json
from pathlib import Path

root = Path('.')
content = (root / "services" / "ocr_text" / "ozelgeler_88_yeni.txt").read_text(encoding="utf-8")
blocks = re.findall(r'\[\s*\{.*?\}\s*\]', content, re.DOTALL)

for i, b in enumerate(blocks):
    parsed = json.loads(b)
    print(f"Block {i}: {len(parsed)} items")
    for item in parsed:
        print(f"  {item.get('ozelge_no')} - {item.get('tarih')}")
