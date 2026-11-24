import sys

import pdfplumber

text_strategy = {"vertical_strategy": "text", "horizontal_strategy": "text"}
with pdfplumber.open(sys.argv[1]) as pdf:
    print("page | tables(lines) | tables(text) | line objects | rect objects")
    for n, page in enumerate(pdf.pages, 1):
        print(n, "|", len(page.find_tables()), "|", len(page.find_tables(text_strategy)), "|",
              len(page.lines), "|", len(page.rects))