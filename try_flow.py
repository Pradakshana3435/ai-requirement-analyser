import sys

import pdfplumber

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

key = "classify requirements into"
with pdfplumber.open(sys.argv[1]) as pdf:
    for mode in (False, True):
        text = "\n".join((p.extract_text(use_text_flow=mode) or "") for p in pdf.pages)
        i = text.find(key)
        print(f"--- use_text_flow={mode}, found at {i}")
        if i != -1:
            print(repr(text[max(0, i - 80): i + 260]))