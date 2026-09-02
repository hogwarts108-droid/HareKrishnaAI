import json
import re

# Test the fixed normalization
def _normalize_entry(entry):
    if not isinstance(entry, dict):
        return entry
    source = str(entry.get("source") or "")
    chapter = str(entry.get("chapter") or "")
    verse = str(entry.get("verse") or "")

    # If verse already contains dots (e.g., "1.3" or "1.2.6"), it's a full reference
    # Don't split it again - just clear redundant chapter
    if verse and re.match(r"^\d+\.", verse):
        # verse is already full reference, ignore chapter
        chapter = ""
    # Only split verse if it doesn't already have chapter embedded
    elif not chapter and isinstance(verse, str) and re.search(r"^\d+(?:\.\d+)+$", verse.strip()):
        parts = verse.strip().split(".")
        if len(parts) >= 2:
            chapter = parts[0]
            verse = ".".join(parts[1:]) if len(parts) > 2 else parts[1]
    elif chapter and not verse:
        verse = chapter

    # Build reference
    ref_parts = []
    if source:
        ref_parts.append(str(source))
    if chapter:
        ref_parts.append(str(chapter))
    if verse and verse.lower() != "full":
        ref_parts.append(str(verse))
    reference = " ".join(ref_parts)
    
    return {"source": source, "chapter": chapter, "verse": verse, "reference": reference}

# Test cases
tests = [
    {"source": "Bhagavad Gita", "chapter": "1", "verse": "1.3"},
    {"source": "Bhagavad Gita", "chapter": "1", "verse": "1.1"},
    {"source": "", "chapter": "", "verse": "1.3"},
    {"source": "Bhagavad Gita", "chapter": "", "verse": "1.3"},
]

print("Testing normalization:")
for test in tests:
    result = _normalize_entry(test)
    print(f"Input: {test}")
    print(f"  -> chapter={result['chapter']!r}, verse={result['verse']!r}, ref={result['reference']!r}")
    print()
