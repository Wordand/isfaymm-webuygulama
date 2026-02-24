import pdfplumber
with pdfplumber.open("kdvtebligi.pdf") as pdf:
    page = pdf.pages[26]
    lines = page.extract_text().split('\n')
    for line in lines[:40]:
        print(line)
