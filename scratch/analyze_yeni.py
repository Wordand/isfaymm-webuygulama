import re
import json
from pathlib import Path

root = Path('.')
content = (root / "services" / "ocr_text" / "ozelgeler_88_yeni.txt").read_text(encoding="utf-8")
blocks = re.findall(r'\[\s*\{.*?\}\s*\]', content, re.DOTALL)

items = []
for b in blocks:
    items.extend(json.loads(b))

print("Total items parsed:", len(items))
for idx, item in enumerate(items):
    print(f"{idx}: {item.get('ozelge_no')} - {item.get('tarih')} - {item.get('konu')[:40]}...")
