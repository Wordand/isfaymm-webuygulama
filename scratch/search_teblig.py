import pdfplumber
import os

pdf_path = r"c:\Users\lalel\Desktop\webuygulama\webuygulama\kurumlarvergisiteblig.pdf"

if not os.path.exists(pdf_path):
    print("PDF not found at:", pdf_path)
    sys.exit(1)

with pdfplumber.open(pdf_path) as pdf:
    print(f"Total pages: {len(pdf.pages)}")
    for i, page in enumerate(pdf.pages):
        text = page.extract_text() or ""
        if "Örnek 4" in text or "2.700.000" in text or "9903" in text:
            print(f"--- Page {i+1} ---")
            lines = text.split("\n")
            for line in lines:
                if any(k in line for k in ["Örnek 4", "2.700.000", "500.000", "2.200.000", "1.900.000"]):
                    print(line)
