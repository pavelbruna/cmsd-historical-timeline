#!/usr/bin/env python3
"""Progressive extraction for 6L.pdf with multiple strategies"""

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

pdf_path = Path("data/raw/pdfs/6L.pdf")
output_dir = Path("data/processed/gemini_ultra")

def pdf_to_image_bytes(pdf_path: Path, dpi: int = 200, max_size_mb: int = 15) -> bytes:
    """Convert PDF to image with specified DPI and compression"""
    doc = fitz.open(str(pdf_path))
    page = doc[0]

    zoom = dpi / 72
    mat = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat)

    img_data = pix.tobytes("png")
    img = Image.open(io.BytesIO(img_data))

    # Resize to fit
    max_pixels = (3072, 3072)
    img.thumbnail(max_pixels, Image.Resampling.LANCZOS)

    if img.mode in ('RGBA', 'LA', 'P'):
        img = img.convert('RGB')

    # Start with quality 85
    quality = 85
    buffer = io.BytesIO()
    img.save(buffer, format='JPEG', quality=quality, optimize=True)
    img_bytes = buffer.getvalue()

    # Compress until under target
    target_size = max_size_mb * 1024 * 1024
    while len(img_bytes) > target_size and quality > 50:
        quality -= 5
        buffer = io.BytesIO()
        img.save(buffer, format='JPEG', quality=quality, optimize=True)
        img_bytes = buffer.getvalue()

    doc.close()
    print(f"  Image: {len(img_bytes)/1024/1024:.2f} MB (quality={quality}, dpi={dpi})")
    return img_bytes

def extract_with_gemini(image_bytes: bytes, pdf_name: str) -> list:
    """Extract using Gemini"""

    prompt = f"""Analyzuješ HUSTOU českou historickou infografiku/časovou osu.

ULTRA EXTRACTION MODE - Extrahuj ABSOLUTNĚ VŠECHNO!

ČTI KAŽDÝ PIXEL:
- Všechny nadpisy (velké i malé)
- Každý text, štítek, poznámku
- Všechny datumy a roky
- Jména u portrétů
- Názvy událostí, bitev, dynastií
- Značky století a epoch
- Geografické názvy
- Text v boxech, bublinách
- Popisky obrázků
- Čísla, symboly, ikony s textem
- VŠE CO OBSAHUJE HISTORICKOU INFORMACI!

OČEKÁVÁNO: 100-150+ událostí z této stránky!

Pro KAŽDOU informaci vytvoř JSON:
{{
  "year": ROK (záporný pro př.n.l., kladný pro n.l.),
  "year_end": KONEC nebo null,
  "title": "Název události v češtině",
  "description": "Detailní popis",
  "category": "religion/war/politics/discovery/culture/science/economics",
  "region": "Oblast",
  "importance": 1-5,
  "tags": ["tagy"],
  "people": ["Osoby"],
  "places": ["Místa"],
  "bible_refs": ["Bible ref"],
  "source_page": "{pdf_name}"
}}

PRAVIDLA:
✓ Extrahuj MINIMÁLNĚ 80-100 událostí!
✓ České znaky: č š ž ř ů ě ý á í ú ň ť ď
✓ př.n.l. = záporný rok
✓ n.l. = kladný rok
✓ I malé detaily jsou důležité!
✓ Nepřeskakuj NIC!

Vrať POUZE JSON array (bez markdown):"""

    try:
        image_part = {'mime_type': 'image/jpeg', 'data': image_bytes}
        response = model.generate_content([prompt, image_part])
        response_text = response.text.strip()

        # Clean
        if response_text.startswith("```json"):
            response_text = response_text[7:]
        if response_text.startswith("```"):
            response_text = response_text[3:]
        if response_text.endswith("```"):
            response_text = response_text[:-3]
        response_text = response_text.strip()

        events = json.loads(response_text)
        return events

    except json.JSONDecodeError as e:
        print(f"  [JSON ERROR] {e}")
        # Save raw response
        raw_file = output_dir / f"6L_raw_attempt.txt"
        with open(raw_file, "w", encoding="utf-8") as f:
            f.write(response_text)
        raise
    except Exception as e:
        print(f"  [ERROR] {e}")
        raise

def try_extraction_strategy(dpi: int, attempt: int) -> list:
    """Try extraction with given DPI"""
    print(f"\n{'='*70}")
    print(f"ATTEMPT {attempt}: DPI={dpi}")
    print('='*70)

    try:
        img_bytes = pdf_to_image_bytes(pdf_path, dpi=dpi, max_size_mb=15)
        events = extract_with_gemini(img_bytes, "6L")
        print(f"  ✓ SUCCESS: {len(events)} events extracted!")
        return events
    except Exception as e:
        print(f"  ✗ FAILED: {e}")
        return None

def main():
    """Progressive extraction strategy"""
    print("="*70)
    print("PROGRESSIVE EXTRACTION: 6L.pdf")
    print("="*70)
    print(f"File size: 41.9 MB (largest PDF)")
    print(f"Strategy: Try decreasing DPI until success\n")

    strategies = [
        (180, "High quality (DPI 180)"),
        (150, "Medium quality (DPI 150)"),
        (120, "Lower quality (DPI 120)"),
        (100, "Minimum quality (DPI 100)"),
    ]

    for attempt, (dpi, description) in enumerate(strategies, 1):
        print(f"\n[{attempt}/{len(strategies)}] {description}")

        events = try_extraction_strategy(dpi, attempt)

        if events:
            # Save
            output_file = output_dir / "6L_gemini.json"
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(events, f, ensure_ascii=False, indent=2)

            print(f"\n{'='*70}")
            print(f"SUCCESS! Extracted {len(events)} events from 6L.pdf")
            print(f"Strategy that worked: DPI {dpi}")
            print(f"Saved to: {output_file}")
            print('='*70)
            return events

    print(f"\n{'='*70}")
    print("ALL STRATEGIES FAILED")
    print("Consider splitting PDF into regions or using different model")
    print('='*70)
    return None

if __name__ == "__main__":
    result = main()
    if not result:
        print("\nNext steps:")
        print("1. Try splitting PDF into 4 quadrants")
        print("2. Try different Gemini model (gemini-2.5-pro)")
        print("3. Use manual annotation")
