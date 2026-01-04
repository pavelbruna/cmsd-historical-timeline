#!/usr/bin/env python3
"""
CMSD - Single PDF Extraction for Analysis
Extract from a single PDF to test Left pages and problematic PDFs
"""

import os
import json
import base64
from pathlib import Path
from typing import List, Dict, Any
import anthropic
import fitz
from PIL import Image
import io

PROJECT_ROOT = Path(__file__).parent.parent
PDFS_DIR = PROJECT_ROOT / "data" / "raw" / "pdfs"
OUTPUT_DIR = PROJECT_ROOT / "data" / "processed"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def pdf_to_base64_image(pdf_path: Path, dpi: int = 150) -> str:
    """Convert PDF to optimized image (< 5MB for Claude API)"""
    print(f"Converting {pdf_path.name} to image (DPI: {dpi})...")

    doc = fitz.open(str(pdf_path))
    page = doc[0]

    zoom = dpi / 72
    mat = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat)

    img_data = pix.tobytes("png")
    img = Image.open(io.BytesIO(img_data))

    # Claude API limit: 5MB (but base64 adds ~33% overhead!)
    # Target: 3.7 MB raw = ~5 MB base64
    target_size = 3.7 * 1024 * 1024

    # Start with aggressive JPEG compression
    max_size = (2048, 2048)
    img.thumbnail(max_size, Image.Resampling.LANCZOS)

    buffer = io.BytesIO()
    if img.mode in ('RGBA', 'LA', 'P'):
        img = img.convert('RGB')
    img.save(buffer, format='JPEG', quality=75, optimize=True)
    img_bytes = buffer.getvalue()

    # Auto-resize loop until we hit target
    while len(img_bytes) > target_size:
        max_size = (int(max_size[0] * 0.85), int(max_size[1] * 0.85))
        img.thumbnail(max_size, Image.Resampling.LANCZOS)
        buffer = io.BytesIO()
        img.save(buffer, format='JPEG', quality=70, optimize=True)
        img_bytes = buffer.getvalue()
        print(f"    Resizing to {max_size[0]}x{max_size[1]}, size: {len(img_bytes) / 1024 / 1024:.2f} MB")

    img_base64 = base64.b64encode(img_bytes).decode('utf-8')
    doc.close()

    base64_size_mb = len(img_base64.encode('utf-8')) / 1024 / 1024
    print(f"  Image size: {len(img_bytes) / 1024 / 1024:.2f} MB (base64: {base64_size_mb:.2f} MB)")
    return img_base64


def extract_single_pdf(client: anthropic.Anthropic, image_base64: str, pdf_name: str) -> List[Dict[str, Any]]:
    """Extract from single PDF using Claude Vision"""
    print(f"Extracting from {pdf_name}...")

    prompt = f"""Analyzuješ českou historickou infografiku/časovou osu.

TVŮJ ÚKOL: Extrahuj VŠECHNY historické informace které vidíš.

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

Pro KAŽDOU událost vytvoř JSON:
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
✓ Extrahuj MINIMÁLNĚ 20-30 událostí
✓ Zachovej VŠECHNY české znaky (č, š, ž, ř, ů, ě, ý, á, í, ú)
✓ př.n.l./BC = záporný rok (-500)
✓ n.l./AD = kladný rok (1500)
✓ Pokud vidíš jen rok bez popisu, vytvoř událost "Rok XXXX"
✓ Nepřeskakuj malé detaily!

Vrať POUZE validní JSON array (žádný jiný text):"""

    try:
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=16000,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": image_base64}},
                    {"type": "text", "text": prompt}
                ],
            }],
        )

        response_text = message.content[0].text.strip()

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
        print(f"  [OK] Extracted {len(events)} events")
        return events

    except json.JSONDecodeError as e:
        print(f"  [ERROR] JSON parse: {e}")
        # Save for debugging
        debug_file = OUTPUT_DIR / f"{pdf_name}_debug_raw.txt"
        with open(debug_file, "w", encoding="utf-8") as f:
            f.write(response_text)
        print(f"  Raw response saved to {debug_file.name}")
        return []
    except Exception as e:
        print(f"  [ERROR] API: {e}")
        return []


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python extract_single.py <pdf_filename>")
        print("Example: python extract_single.py 1L.pdf")
        sys.exit(1)

    pdf_filename = sys.argv[1]
    pdf_path = PDFS_DIR / pdf_filename

    if not pdf_path.exists():
        print(f"[ERROR] PDF not found: {pdf_path}")
        sys.exit(1)

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("[ERROR] ANTHROPIC_API_KEY not set!")
        sys.exit(1)

    client = anthropic.Anthropic(api_key=api_key)

    print("="*70)
    print(f"EXTRACTING: {pdf_filename}")
    print("="*70)

    # Convert to image
    img_base64 = pdf_to_base64_image(pdf_path, dpi=150)

    # Extract
    events = extract_single_pdf(client, img_base64, pdf_path.stem)

    # Save
    if events:
        output_file = OUTPUT_DIR / f"{pdf_path.stem}_single.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(events, f, ensure_ascii=False, indent=2)
        print(f"\n[SUCCESS] Saved {len(events)} events to {output_file.name}")
    else:
        print(f"\n[WARNING] No events extracted from {pdf_filename}")
