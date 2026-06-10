import json
import re
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parents[1]

OCR_DIR = ROOT / "services" / "ocr_text"
OUT_FILE = ROOT / "static" / "data" / "ozelgeler_envanter.json"


def extract_first(pattern, text):
    m = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
    return m.group(1).strip() if m else ""


def detect_tesvik_rejimleri(text):
    rejimler = []

    patterns = [
        r"2009\/15199",
        r"2012\/3305",
        r"2014\/6058",
        r"2015\/7496",
        r"2016\/8706",
        r"2016\/9139",
        r"2017\/9917",
        r"2019\/1950",
        r"2025\/9903"
    ]

    for p in patterns:
        if re.search(p, text):
            rejimler.append(p)

    return sorted(list(set(rejimler)))


def detect_category(text):
    lower = text.lower()

    rules = [
        ("Tevsi Yatırım", [
            "tevsi yatırım",
            "ayrı hesaplarda izlenmek",
            "oranlama yöntemi",
            "tevsi"
        ]),

        ("Diğer Faaliyet Kazancı", [
            "diğer faaliyetlerden elde edilen kazanç",
            "diğer faaliyet kazancı",
            "yatırım döneminde"
        ]),

        ("Yatırıma Katkı Tutarı", [
            "yatırıma katkı tutarı",
            "yatırıma katkı oranı",
            "katkı tutarı"
        ]),

        ("Yatırım Harcaması", [
            "yatırım harcaması",
            "yatırım harcaması",
            "makine ve teçhizat",
            "erp",
            "lisans",
            "arsa",
            "royalti",
            "yedek parça"
        ]),

        ("Tamamlama Vizesi", [
            "tamamlama vizesi"
        ]),

        ("Devir", [
            "devir",
            "devralınan",
            "birleşme",
            "nev'i değişikliği"
        ]),

        ("Endeksleme", [
            "yeniden değerleme",
            "endeksleme"
        ]),

        ("Birden Fazla Teşvik Belgesi", [
            "iki ayrı yatırım teşvik belgesi",
            "birden fazla yatırım teşvik belgesi"
        ])
    ]

    for category, keywords in rules:
        if any(k in lower for k in keywords):
            return category

    return "Diğer"


def extract_keywords(text):

    keywords = []

    keyword_pool = [
        "tevsi yatırım",
        "diğer faaliyet",
        "yatırıma katkı",
        "yatırım harcaması",
        "arsa",
        "arazi",
        "royalti",
        "erp",
        "lisans",
        "finansal kiralama",
        "devir",
        "birleşme",
        "tamamlama vizesi",
        "endeksleme",
        "yeniden değerleme",
        "teşvik belgesi",
        "komple yeni yatırım",
        "makine",
        "teçhizat",
        "yatırım dönemi"
    ]

    lower = text.lower()

    for kw in keyword_pool:
        if kw in lower:
            keywords.append(kw)

    return keywords


def build_envanter():

    items = []

    txt_files = sorted(OCR_DIR.glob("*.txt"))

    print(f"{len(txt_files)} TXT bulundu")

    for txt_file in txt_files:

        text = txt_file.read_text(
            encoding="utf-8",
            errors="ignore"
        )

        ozelge_no = extract_first(
            r"Özelge No\s*(.*?)\n",
            text
        )

        ozelge_tarihi = extract_first(
            r"Özelge Tarihi\s*(.*?)\n",
            text
        )

        konu = extract_first(
            r"Konu\s*(.*?)\n",
            text
        )

        sonuc = ""

        sonuc_match = re.search(
            r"Bu hüküm ve açıklamalara göre(.{0,2500})",
            text,
            re.IGNORECASE | re.DOTALL
        )

        if sonuc_match:
            sonuc = sonuc_match.group(0).replace("\n", " ").strip()

        item = {
            "filename": txt_file.name,
            "ozelge_no": ozelge_no,
            "ozelge_tarihi": ozelge_tarihi,
            "konu": konu,
            "tesvik_rejimleri": detect_tesvik_rejimleri(text),
            "kategori": detect_category(text),
            "anahtar_kelimeler": extract_keywords(text),
            "sonuc": sonuc[:3000],
            "search_text": text[:15000]
        }

        items.append(item)

    payload = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "count": len(items),
        "items": items
    }

    OUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    OUT_FILE.write_text(
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )

    print("Tamamlandı")
    print(OUT_FILE)


if __name__ == "__main__":
    build_envanter()