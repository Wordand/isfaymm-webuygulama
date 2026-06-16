import pdfplumber

pdf_path = r"c:\Users\lalel\Desktop\webuygulama\webuygulama\kurumlarvergisiteblig.pdf"
out_path = r"c:\Users\lalel\Desktop\webuygulama\webuygulama\scratch\teblig_ornek4.txt"

with pdfplumber.open(pdf_path) as pdf:
    found_text = []
    for i, page in enumerate(pdf.pages):
        text = page.extract_text() or ""
        if "Örnek 4" in text:
            found_text.append(f"=== Page {i+1} ===")
            found_text.append(text)
    
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(found_text))

print("Done! Extracted pages to scratch/teblig_ornek4.txt")
