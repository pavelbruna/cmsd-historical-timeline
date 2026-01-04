#!/usr/bin/env python3
"""
CMSD - Extraction with Groq Vision (Llama 3.2 90B Vision)
SUPER FAST extraction for large PDFs!
"""

import os
import json
import base64
from pathlib import Path
from typing import List, Dict, Any
from groq import Groq
import fitz
from PIL import Image
import io

PROJECT_ROOT = Path(__file__).parent.parent
PDFS_DIR = PROJECT_ROOT / "data" / "raw" / "pdfs"
OUTPUT_DIR = PROJECT_ROOT / "data" / "processed"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def pdf_to_base64_image(pdf_path: Path, dpi: int = 200) -> str:
    """Convert PDF to image for Groq Vision"""
    print(f"Converting {pdf_path.name} to image (DPI: {dpi})...")

    doc = fitz.open(str(pdf_path))
    page = doc[0]

    # Higher DPI for better quality
    zoom = dpi / 72
    mat = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat)

    img_data = pix.tobytes("png")
    img = Image.open(io.BytesIO(img_data))

    # Good quality size
    max_size = (2560, 2560)
    img.thumbnail(max_size, Image.Resampling.LANCZOS)

    buffer = io.BytesIO()
    if img.mode in ('RGBA', 'LA', 'P'):
        img = img.convert('RGB')

    # High quality JPEG
    img.save(buffer, format='JPEG', quality=92, optimize=True)
    img_bytes = buffer.getvalue()

    # If too large, reduce
    max_size_mb = 10  # Groq limit
    while len(img_bytes) > max_size_mb * 1024 * 1024:
        max_size = (int(max_size[0] * 0.85), int(max_size[1] * 0.85))
        img.thumbnail(max_size, Image.Resampling.LANCZOS)
        buffer = io.BytesIO()
        img.save(buffer, format='JPEG', quality=85, optimize=True)
        img_bytes = buffer.getvalue()
        print(f"    Resizing to {max_size[0]}x{max_size[1]}, size: {len(img_bytes) / 1024 / 1024:.2f} MB")

    img_base64 = base64.b64encode(img_bytes).decode('utf-8')
    doc.close()

    size_mb = len(img_bytes) / 1024 / 1024
    print(f"  Image size: {size_mb:.2f} MB")
    return img_base64


def extract_with_groq(client: Groq, image_base64: str, pdf_name: str) -> List[Dict[str, Any]]:
    """Extract using Groq Vision (Llama 3.2 90B Vision)"""
    print(f"Extracting from {pdf_name} using Groq Vision (ULTRA FAST!)...")

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

Vrať POUZE validní JSON array s událostmi. ŽÁDNÝ jiný text nebo markdown!"""

    try:
        completion = client.chat.completions.create(
            model="llama-3.2-90b-vision-preview",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{image_base64}"
                            }
                        },
                        {
                            "type": "text",
                            "text": prompt
                        }
                    ]
                }
            ],
            temperature=0.1,
            max_tokens=16000,
            top_p=1,
            stream=False,
        )

        response_text = completion.choices[0].message.content.strip()

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
        print(f"  [OK] {len(events)} events extracted in {completion.usage.total_time:.2f}s!")
        print(f"  Speed: {len(events) / completion.usage.total_time:.1f} events/sec")
        return events

    except json.JSONDecodeError as e:
        print(f"  [ERROR] JSON parse: {e}")
        # Save for debugging
        debug_file = OUTPUT_DIR / f"{pdf_name}_groq_raw.txt"
        with open(debug_file, "w", encoding="utf-8") as f:
            f.write(response_text)
        print(f"  Raw response saved to {debug_file.name}")
        return []
    except Exception as e:
        print(f"  [ERROR] API: {e}")
        return []


def extract_single_pdf_groq(pdf_filename: str):
    """Extract single PDF with Groq Vision"""
    pdf_path = PDFS_DIR / pdf_filename

    if not pdf_path.exists():
        print(f"[ERROR] PDF not found: {pdf_path}")
        return []

    # Get API key
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        print("[ERROR] GROQ_API_KEY not set!")
        print("Get your key at: https://console.groq.com")
        return []

    # Configure Groq
    client = Groq(api_key=api_key)

    print("="*70)
    print(f"EXTRACTING WITH GROQ VISION: {pdf_filename}")
    print("="*70)

    # Convert to image
    img_base64 = pdf_to_base64_image(pdf_path, dpi=200)

    # Extract
    events = extract_with_groq(client, img_base64, pdf_path.stem)

    # Save
    if events:
        output_file = OUTPUT_DIR / f"{pdf_path.stem}_groq.json"
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
        print("Usage: python extract_with_groq.py <pdf_filename>")
        print("Example: python extract_with_groq.py 1R.pdf")
        sys.exit(1)

    pdf_filename = sys.argv[1]
    events = extract_single_pdf_groq(pdf_filename)

    if events:
        print(f"\n[SUCCESS] {len(events)} events extracted with Groq!")
