import pdfplumber
import re

pdf_path = r"c:\Users\lalel\Desktop\webuygulama\webuygulama\kurumlarvergisiteblig.pdf"

with pdfplumber.open(pdf_path) as pdf:
    print(f"Total pages: {len(pdf.pages)}")
    for idx, page in enumerate(pdf.pages):
        text = page.extract_text() or ""
        # Search for pattern like "32.2."
        matches = re.findall(r"(32\.2\.\d+[^.\n]+)", text)
        if matches:
            print(f"Page {idx+1}:")
            for m in matches:
                print("  -", m.strip())
