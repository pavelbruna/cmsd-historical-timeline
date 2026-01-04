#!/usr/bin/env python3
"""
CMSD - Extraction with Gemini 2.0 Flash
For PDFs that exceed Claude's 5MB limit
Gemini supports larger images!
"""

import os
import json
import base64
from pathlib import Path
from typing import List, Dict, Any
import google.generativeai as genai
import fitz
from PIL import Image
import io

PROJECT_ROOT = Path(__file__).parent.parent
PDFS_DIR = PROJECT_ROOT / "data" / "raw" / "pdfs"
OUTPUT_DIR = PROJECT_ROOT / "data" / "processed"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def pdf_to_image_bytes(pdf_path: Path, dpi: int = 200) -> bytes:
    """Convert PDF to high-quality image (Gemini supports larger files!)"""
    print(f"Converting {pdf_path.name} to image (DPI: {dpi})...")

    doc = fitz.open(str(pdf_path))
    page = doc[0]

    # Higher DPI for Gemini (supports up to 20MB)
    zoom = dpi / 72
    mat = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat)

    img_data = pix.tobytes("png")
    img = Image.open(io.BytesIO(img_data))

    # Start with good quality
    max_size = (3072, 3072)  # Larger than Claude
    img.thumbnail(max_size, Image.Resampling.LANCZOS)

    buffer = io.BytesIO()
    if img.mode in ('RGBA', 'LA', 'P'):
        img = img.convert('RGB')

    # Try JPEG quality 90 first
    img.save(buffer, format='JPEG', quality=90, optimize=True)
    img_bytes = buffer.getvalue()

    # If > 15MB, compress more
    target_size = 15 * 1024 * 1024
    quality = 90

    while len(img_bytes) > target_size and quality > 60:
        quality -= 10
        buffer = io.BytesIO()
        img.save(buffer, format='JPEG', quality=quality, optimize=True)
        img_bytes = buffer.getvalue()
        print(f"    Compressing: quality={quality}, size={len(img_bytes) / 1024 / 1024:.2f} MB")

    doc.close()

    size_mb = len(img_bytes) / 1024 / 1024
    print(f"  Image size: {size_mb:.2f} MB")
    return img_bytes


def extract_with_gemini(client: genai.GenerativeModel, image_bytes: bytes, pdf_name: str) -> List[Dict[str, Any]]:
    """Extract using Gemini 2.0 Flash"""
    print(f"Extracting from {pdf_name} using Gemini 2.0 Flash...")

    prompt = f"""Analyzuješ HUSTOU českou historickou infografiku/časovou osu.

TVŮJ ÚKOL: Extrahuj VŠECHNY historické události které vidíš na této stránce.

ČTI VŠECHNO:
- Velké nadpisy a titulky
- Malý text a poznámky
- Datumy na časové ose
- Jména u portrétů a obrázků
- Názvy bitev, událostí, období
- Značky roků a století
- Geografické regiony
- Text v boxech, bublinách, štítcích
- Popisky pod obrázky
- VŠECHNY viditelné historické informace

OČEKÁVANÝ VÝSTUP: 30-60+ událostí z této JEDNÉ stránky!

Pro KAŽDOU událost vytvoř JSON objekt:
{{
  "year": ROK (záporný pro př.n.l., kladný pro n.l.),
  "year_end": KONEC_OBDOBÍ nebo null,
  "title": "Název události v češtině",
  "description": "Detailní popis co se stalo",
  "category": "religion/war/politics/discovery/culture/science/economics",
  "region": "Geografická oblast",
  "importance": 1-5,
  "tags": ["klíčová", "slova"],
  "people": ["Jména osob"],
  "places": ["Názvy míst"],
  "bible_refs": ["Biblické odkazy pokud jsou"],
  "source_page": "{pdf_name}"
}}

PRAVIDLA:
✓ Extrahuj MINIMÁLNĚ 30 událostí (toto je hustá infografika!)
✓ Zachovej VŠECHNY české znaky (č, š, ž, ř, ů, ě, ý, á, í, ú)
✓ př.n.l./BC = záporný rok (-500)
✓ n.l./AD = kladný rok (1500)
✓ Pokud vidíš jen rok bez popisu, vytvoř událost "Rok XXXX"
✓ Nepřeskakuj malé detaily!

Vrať POUZE validní JSON array s událostmi. ŽÁDNÝ jiný text!"""

    try:
        # Upload image
        image_part = {
            'mime_type': 'image/jpeg',
            'data': image_bytes
        }

        response = client.generate_content([prompt, image_part])
        response_text = response.text.strip()

        # Clean markdown
        if response_text.startswith("```json"):
            response_text = response_text[7:]
        if response_text.startswith("```"):
            response_text = response_text[3:]
        if response_text.endswith("```"):
            response_text = response_text[:-3]

        response_text = response_text.strip()

        # Parse JSON
        events = json.loads(response_text)
        print(f"  [OK] {len(events)} events extracted")
        return events

    except json.JSONDecodeError as e:
        print(f"  [ERROR] JSON parse: {e}")
        # Save for debugging
        debug_file = OUTPUT_DIR / f"{pdf_name}_gemini_raw.txt"
        with open(debug_file, "w", encoding="utf-8") as f:
            f.write(response_text)
        print(f"  Raw response saved to {debug_file.name}")
        return []
    except Exception as e:
        print(f"  [ERROR] API: {e}")
        return []


def extract_single_pdf_gemini(pdf_filename: str):
    """Extract single PDF with Gemini"""
    pdf_path = PDFS_DIR / pdf_filename

    if not pdf_path.exists():
        print(f"[ERROR] PDF not found: {pdf_path}")
        return []

    # Get API key
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print("[ERROR] GEMINI_API_KEY or GOOGLE_API_KEY not set!")
        print("Get your key at: https://aistudio.google.com/app/apikey")
        return []

    # Configure Gemini
    genai.configure(api_key=api_key)
    # Use latest Gemini 2.5 Flash (with models/ prefix!)
    model = genai.GenerativeModel('models/gemini-2.5-flash')

    print("="*70)
    print(f"EXTRACTING WITH GEMINI: {pdf_filename}")
    print("="*70)

    # Convert to image
    img_bytes = pdf_to_image_bytes(pdf_path, dpi=200)

    # Extract
    events = extract_with_gemini(model, img_bytes, pdf_path.stem)

    # Save
    if events:
        output_file = OUTPUT_DIR / f"{pdf_path.stem}_gemini.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(events, f, ensure_ascii=False, indent=2)
        print(f"\n[SUCCESS] Saved {len(events)} events to {output_file.name}")
        return events
    else:
        print(f"\n[WARNING] No events extracted from {pdf_filename}")
        return []


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python extract_with_gemini.py <pdf_filename>")
        print("Example: python extract_with_gemini.py 1R.pdf")
        sys.exit(1)

    pdf_filename = sys.argv[1]
    events = extract_single_pdf_gemini(pdf_filename)

    if events:
        print(f"\n[SUCCESS] {len(events)} events extracted with Gemini!")
