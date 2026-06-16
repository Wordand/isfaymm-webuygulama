import pdfplumber

pdf_path = r"c:\Users\lalel\Desktop\webuygulama\webuygulama\kurumlarvergisiteblig.pdf"
out_path = r"c:\Users\lalel\Desktop\webuygulama\webuygulama\scratch\extracted_examples.txt"

with pdfplumber.open(pdf_path) as pdf:
    # 0-indexed: page 200 is index 199, page 230 is index 229
    start_page = 205
    end_page = min(235, len(pdf.pages))
    print(f"Reading pages {start_page} to {end_page}...")
    
    extracted_text = []
    for p_num in range(start_page, end_page):
        page = pdf.pages[p_num]
        text = page.extract_text() or ""
        extracted_text.append(f"=== PAGE {p_num + 1} ===")
        extracted_text.append(text)
        
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n\n".join(extracted_text))
        
print("Successfully extracted pages to scratch/extracted_examples.txt")
