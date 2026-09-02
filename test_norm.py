import re

# Test normalization
verse = "4.7"
chapter = ""

print(f"Input: chapter={chapter!r}, verse={verse!r}")

if not chapter and isinstance(verse, str) and re.search(r"^\d+(?:\.\d+)+$", verse.strip()):
    parts = verse.strip().split(".")
    print(f"Parts: {parts}")
    if len(parts) >= 2:
        chapter = parts[0]
        verse = ".".join(parts[1:]) if len(parts) > 2 else parts[1]
        print(f"After split: chapter={chapter!r}, verse={verse!r}")

# Test matching
ref = f"{chapter}.{verse}"
print(f"Final ref: {ref!r}")

# Test match against "1.3"
q = "1.3"
print(f"Does '{q}' == '{ref}'? {q == ref}")
