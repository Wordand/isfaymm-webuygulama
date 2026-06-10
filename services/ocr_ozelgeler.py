from pathlib import Path
import fitz
import easyocr
import numpy as np

PDF_DIR = Path("ozelgeler")
OUT_DIR = Path("ocr_text")

OUT_DIR.mkdir(exist_ok=True)

print("EasyOCR yükleniyor...")
reader = easyocr.Reader(['tr'])

pdfs = list(PDF_DIR.glob("*.pdf"))

print("Toplam PDF:", len(pdfs))

processed = len(list(OUT_DIR.glob("*.txt")))

print("Mevcut TXT:", processed)
print("Kalan:", len(pdfs) - processed)

for i, pdf_file in enumerate(pdfs, start=1):

    txt_file = OUT_DIR / f"{pdf_file.stem}.txt"

    # Daha önce işlendi ise geç
    if txt_file.exists():
        print(f"[{i}/{len(pdfs)}] Atlandı: {pdf_file.name}")
        continue

    try:

        print(f"[{i}/{len(pdfs)}] İşleniyor: {pdf_file.name}")

        doc = fitz.open(pdf_file)

        full_text = []

        for page_num in range(len(doc)):

            page = doc[page_num]

            pix = page.get_pixmap(
                matrix=fitz.Matrix(1.5, 1.5)
            )

            img = np.frombuffer(
                pix.samples,
                dtype=np.uint8
            )

            img = img.reshape(
                pix.height,
                pix.width,
                pix.n
            )

            results = reader.readtext(
                img,
                detail=0
            )

            full_text.extend(results)

        text = "\n".join(full_text)

        txt_file.write_text(
            text,
            encoding="utf-8"
        )

        print(f"Kaydedildi: {txt_file.name}")

    except Exception as e:

        print(f"HATA: {pdf_file.name}")
        print(str(e))

print("TAMAMLANDI")