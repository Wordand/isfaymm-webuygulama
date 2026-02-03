import pdfplumber
import re

pdf_path = r"c:\Users\lalel\Desktop\webuygulama\webuygulama\static\pdf\kurumlarvergisiteblig.pdf"

def analyze_kv_structure(path):
    with pdfplumber.open(path) as pdf:
        print(f"Total Pages: {len(pdf.pages)}")
        print("-" * 30)
        # Check first few pages to understand layout/TOC
        for i in range(0, 5): 
            page = pdf.pages[i]
            text = page.extract_text()
            print(f"--- PAGE {i+1} ---")
            print(text[:800]) 
            print("\n")
            
        print("-" * 30)
        # Check a middle page to see content structure
        mid_page = pdf.pages[50]
        print(f"--- PAGE 51 (Middle) ---")
        print(mid_page.extract_text()[:800])

if __name__ == "__main__":
    analyze_kv_structure(pdf_path)
