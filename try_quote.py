import sys
import unicodedata

from ingest.extract import extract_text

path = sys.argv[1]
with open(path, "rb") as f:
    doc = extract_text(path, f.read())
text = doc.raw_text

odd = sorted({c for c in text if ord(c) > 127})
print("non-ASCII characters in the extracted text:")
for c in odd:
    print(f"  U+{ord(c):04X} {unicodedata.name(c, '?')}  x{text.count(c)}")

print("\nhyphen-then-newline cases:", text.count("-\n"))

shown = 0
start = 0
while shown < 3:
    i = text.find("lassif", start)
    if i == -1:
        break
    print("\ncontext:", repr(text[max(0, i - 100): i + 140]))
    start = i + 1
    shown += 1