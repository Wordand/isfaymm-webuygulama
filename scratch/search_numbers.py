from pathlib import Path
import re

root = Path('.')
content = (root / "services" / "ocr_text" / "ozelgeler_88_yeni.txt").read_text(encoding="utf-8")

numbers = ["174093", "180023", "2995", "32576", "39328", "53376", "19341373"]

for num in numbers:
    matches = re.findall(rf".*{num}.*", content)
    print(f"Number {num}: matches = {matches}")
