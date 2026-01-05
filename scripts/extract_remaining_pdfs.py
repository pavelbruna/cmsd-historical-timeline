#!/usr/bin/env python3
"""
Extract remaining 7 PDFs with Gemini 2.5 Flash
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
import time

PROJECT_ROOT = Path(__file__).parent.parent
PDFS_DIR = PROJECT_ROOT / "data" / "raw" / "pdfs"
OUTPUT_DIR = PROJECT_ROOT / "data" / "processed" / "gemini_ultra"

# Remaining PDFs to process
REMAINING_PDFS = [
    "7L.pdf",
    "7R.pdf",
    "8L.pdf",
    "8R.pdf",
    "PredniPreds.pdf",
    "zadniPredsLic.pdf",
    "zadniPredsRub.pdf"
]

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def pdf_to_image_bytes(pdf_path: Path, dpi: int = 200) -> bytes:
    """Convert PDF to high-quality image"""
    doc = fitz.open(str(pdf_path))
    page = doc[0]

    zoom = dpi / 72
    mat = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat)

    img_data = pix.tobytes("png")
    img = Image.open(io.BytesIO(img_data))

    # Good quality
    max_size = (3072, 3072)
    img.thumbnail(max_size, Image.Resampling.LANCZOS)

    buffer = io.BytesIO()
    if img.mode in ('RGBA', 'LA', 'P'):
        img = img.convert('RGB')

    # High quality JPEG
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

    doc.close()
    return img_bytes


def extract_with_gemini(model: genai.GenerativeModel, image_bytes: bytes, pdf_name: str) -> List[Dict[str, Any]]:
    """Extract using Gemini 2.5 Flash - ULTRA mode!"""

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

OČEKÁVÁNO: 50-100+ událostí z JEDNÉ stránky!

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
✓ Extrahuj MINIMÁLNĚ 40-50 událostí!
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
        print(f"  [OK] {len(events)} events")
        return events

    except json.JSONDecodeError as e:
        print(f"  [ERROR] JSON: {e}")
        debug_file = OUTPUT_DIR / f"{pdf_name}_raw.txt"
        with open(debug_file, "w", encoding="utf-8") as f:
            f.write(response_text)
        return []
    except Exception as e:
        print(f"  [ERROR] {e}")
        return []


def extract_remaining_pdfs():
    """Extract remaining 7 PDFs"""
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print("[ERROR] GEMINI_API_KEY not set!")
        return

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('models/gemini-2.5-flash')

    all_events = []
    stats = {"processed": 0, "total_events": 0, "by_pdf": {}, "errors": []}

    print("="*70)
    print("EXTRACTING REMAINING 7 PDFs WITH GEMINI 2.5 FLASH")
    print("="*70)
    print(f"Remaining PDFs: {len(REMAINING_PDFS)}")
    print()

    for pdf_name in REMAINING_PDFS:
        pdf_path = PDFS_DIR / pdf_name

        if not pdf_path.exists():
            print(f"[SKIP] {pdf_name} - not found")
            continue

        try:
            print(f"\n[{stats['processed']+1}/{len(REMAINING_PDFS)}] {pdf_name}")
            print("-" * 70)

            # Convert
            img_bytes = pdf_to_image_bytes(pdf_path, dpi=200)
            size_mb = len(img_bytes) / 1024 / 1024
            print(f"  Image: {size_mb:.2f} MB")

            # Extract
            events = extract_with_gemini(model, img_bytes, pdf_path.stem)

            all_events.extend(events)
            stats["processed"] += 1
            stats["total_events"] += len(events)
            stats["by_pdf"][pdf_name] = len(events)

            # Save per-PDF
            output_file = OUTPUT_DIR / f"{pdf_path.stem}_gemini.json"
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(events, f, ensure_ascii=False, indent=2)

            # Rate limit: wait 3s between requests
            if pdf_name != REMAINING_PDFS[-1]:
                print("  Waiting 3s...")
                time.sleep(3)

        except Exception as e:
            print(f"  [FAILED] {e}")
            stats["errors"].append(pdf_name)
            stats["by_pdf"][pdf_name] = 0

    # Save combined remaining
    combined_file = OUTPUT_DIR / "remaining_7_gemini.json"
    with open(combined_file, "w", encoding="utf-8") as f:
        json.dump(all_events, f, ensure_ascii=False, indent=2)

    # Save stats
    stats_file = OUTPUT_DIR / "remaining_7_stats.json"
    with open(stats_file, "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)

    print("\n" + "="*70)
    print("REMAINING PDFs EXTRACTION COMPLETE")
    print("="*70)
    print(f"PDFs processed: {stats['processed']}/{len(REMAINING_PDFS)}")
    print(f"Total new events: {stats['total_events']}")
    print(f"Average per PDF: {stats['total_events'] / max(stats['processed'], 1):.1f}")

    print(f"\nBy PDF:")
    for pdf, count in stats['by_pdf'].items():
        print(f"  {pdf:25s} {count:4d} events")

    if stats['errors']:
        print(f"\nErrors: {len(stats['errors'])}")
        for err in stats['errors']:
            print(f"  - {err}")

    return all_events, stats


if __name__ == "__main__":
    print("CMSD - Extracting Remaining 7 PDFs")
    print("Target: Maximum events from final PDFs!")
    print()

    events, stats = extract_remaining_pdfs()

    print(f"\n[SUCCESS] {len(events)} new events extracted!")
    print("Next: Run merge script to combine with existing data")
