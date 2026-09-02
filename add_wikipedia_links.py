#!/usr/bin/env python3
"""Add Wikipedia links to all figures"""
import json

wikipedia_links = {
    "Balarama": "https://en.wikipedia.org/wiki/Balarama",
    "Radha": "https://en.wikipedia.org/wiki/Radha",
    "Arjuna": "https://en.wikipedia.org/wiki/Arjuna",
    "Devaki": "https://en.wikipedia.org/wiki/Devaki",
    "Vasudeva": "https://en.wikipedia.org/wiki/Vasudeva",
    "Kamsa": "https://en.wikipedia.org/wiki/Kamsa",
    "Nanda": "https://en.wikipedia.org/wiki/Nanda_(mythology)",
    "Yasoda": "https://en.wikipedia.org/wiki/Yasoda",
    "Indra": "https://en.wikipedia.org/wiki/Indra",
    "Brahma": "https://en.wikipedia.org/wiki/Brahma",
    "Vishnu": "https://en.wikipedia.org/wiki/Vishnu",
    "Shiva": "https://en.wikipedia.org/wiki/Shiva",
    "Krishna": "https://en.wikipedia.org/wiki/Krishna",
}

# Load figures
with open("data/scriptures/figures_introductions.json", "r", encoding="utf-8") as f:
    figures = json.load(f)

# Add Wikipedia links
for fig in figures:
    source = fig.get("source")
    if source in wikipedia_links:
        fig["wikipedia"] = wikipedia_links[source]
        print(f"OK {source}")

# Save
with open("data/scriptures/figures_introductions.json", "w", encoding="utf-8") as f:
    json.dump(figures, f, indent=2, ensure_ascii=False)

print("\nOK Wikipedia links added!")
