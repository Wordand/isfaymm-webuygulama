
import pdfplumber

pdf_path = r"C:\Users\lalel\Desktop\webuygulama\beyannameler\isfa byn 2024.pdf"
with pdfplumber.open(pdf_path) as pdf:
    for i, page in enumerate(pdf.pages):
        print(f"--- PAGE {i+1} ---")
        print(page.extract_text())
