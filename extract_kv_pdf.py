import fitz
import json

def analyze_pdf(pdf_path):
    doc = fitz.open(pdf_path)
    print(f"Total pages: {len(doc)}")
    
    # Check page 1
    page = doc[0]
    text = page.get_text()
    
    print("--- Page 1 ---")
    print(text[:1000].encode('utf-8').decode('utf-8'))

if __name__ == "__main__":
    analyze_pdf(r"C:\Users\lalel\Desktop\webuygulama\webuygulama\kurumlarvergisiteblig.pdf")
