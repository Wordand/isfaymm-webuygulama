import pdfplumber

path = r"c:\Users\lalel\Desktop\webuygulama\webuygulama\kurumlarvergisiteblig.pdf"
output_path = r"c:\Users\lalel\Desktop\webuygulama\webuygulama\scratch\extracted_teblig.txt"

try:
    with pdfplumber.open(path) as pdf:
        print(f"Total Pages: {len(pdf.pages)}")
        found = False
        with open(output_path, "w", encoding="utf-8") as out_f:
            for idx in range(len(pdf.pages)):
                text = pdf.pages[idx].extract_text()
                if text and ("32.2. İndirimli kurumlar" in text or "32.2.1." in text):
                    print(f"Found on page {idx+1}")
                    found = True
                    # Write from this page to the next few pages
                    for j in range(idx, min(idx + 25, len(pdf.pages))):
                        page_text = pdf.pages[j].extract_text()
                        out_f.write(f"\n--- Page {j+1} ---\n")
                        out_f.write(page_text)
                    break
        if not found:
            print("Not found in the PDF.")
        else:
            print(f"Extracted section written to {output_path}")
except Exception as e:
    print(f"Error: {e}")
