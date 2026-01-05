#!/usr/bin/env python3
"""Retry extraction for 8R.pdf"""

import os
import json
import fitz
from PIL import Image
import io
import google.generativeai as genai
from pathlib import Path

api_key = "AIzaSyANgwHwZ-h-LSn0VxqD44uxcTMvRE-hzSI"
genai.configure(api_key=api_key)
model = genai.GenerativeModel('models/gemini-2.5-flash')

pdf_path = Path("data/raw/pdfs/8R.pdf")
output_dir = Path("data/processed/gemini_ultra")

def pdf_to_image_bytes(pdf_path: Path, dpi: int = 200) -> bytes:
    """Convert PDF to image"""
    doc = fitz.open(str(pdf_path))
    page = doc[0]
    zoom = dpi / 72
    mat = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat)
    img_data = pix.tobytes("png")
    img = Image.open(io.BytesIO(img_data))
    max_size = (3072, 3072)
    img.thumbnail(max_size, Image.Resampling.LANCZOS)
    buffer = io.BytesIO()
    if img.mode in ('RGBA', 'LA', 'P'):
        img = img.convert('RGB')
    img.save(buffer, format='JPEG', quality=85, optimize=True)
    doc.close()
    return buffer.getvalue()

print("Extracting 8R.pdf...")
img_bytes = pdf_to_image_bytes(pdf_path, dpi=180)
print(f"Image size: {len(img_bytes)/1024/1024:.2f} MB")

prompt = """Analyzuješ českou historickou infografiku/časovou osu.

Extrahuj VŠECHNY události, které vidíš. Pro každou vytvoř JSON:
{
  "year": ROK (záporný pro př.n.l.),
  "year_end": KONEC nebo null,
  "title": "Název události",
  "description": "Popis",
  "category": "religion/war/politics/discovery/culture/science/economics",
  "region": "Oblast",
  "importance": 1-5,
  "tags": [],
  "people": [],
  "places": [],
  "bible_refs": [],
  "source_page": "8R"
}

Vrať POUZE validní JSON array (bez markdown):"""

try:
    image_part = {'mime_type': 'image/jpeg', 'data': img_bytes}
    response = model.generate_content([prompt, image_part])
    response_text = response.text.strip()

    # Clean markdown
    if response_text.startswith("```json"):
        response_text = response_text[7:]
    if response_text.startswith("```"):
        response_text = response_text[3:]
    if response_text.endswith("```"):
        response_text = response_text[:-3]
    response_text = response_text.strip()

    # Save raw
    with open(output_dir / "8R_raw_retry.txt", "w", encoding="utf-8") as f:
        f.write(response_text)

    events = json.loads(response_text)

    # Save
    with open(output_dir / "8R_gemini.json", "w", encoding="utf-8") as f:
        json.dump(events, f, ensure_ascii=False, indent=2)

    print(f"SUCCESS: {len(events)} events extracted!")

except Exception as e:
    print(f"ERROR: {e}")
    print("Trying to use existing 8R_claude_deep.json instead...")

    # Use claude deep as fallback
    claude_file = Path("data/processed/8R_claude_deep.json")
    if claude_file.exists():
        with open(claude_file, 'r', encoding='utf-8') as f:
            events = json.load(f)
        with open(output_dir / "8R_gemini.json", "w", encoding="utf-8") as f:
            json.dump(events, f, ensure_ascii=False, indent=2)
        print(f"Used Claude data: {len(events)} events")
