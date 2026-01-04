#!/usr/bin/env python3
"""
CMSD - ULTRA EXTRACTION of ALL PDFs with Gemini 2.5 Flash
Re-extract everything for maximum data yield!
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


def extract_all_pdfs():
    """Extract ALL PDFs with Gemini"""
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print("[ERROR] GEMINI_API_KEY not set!")
        return

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('models/gemini-2.5-flash')

    # ALL PDFs to process
    all_pdfs = sorted(PDFS_DIR.glob("*.pdf"))

    all_events = []
    stats = {"processed": 0, "total_events": 0, "by_pdf": {}, "errors": []}

    print("="*70)
    print("ULTRA EXTRACTION WITH GEMINI 2.5 FLASH")
    print("="*70)
    print(f"Total PDFs: {len(all_pdfs)}")
    print()

    for pdf_path in all_pdfs:
        pdf_name = pdf_path.name

        try:
            print(f"\n[{stats['processed']+1}/{len(all_pdfs)}] {pdf_name}")
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
            if pdf_path != all_pdfs[-1]:
                print("  Waiting 3s...")
                time.sleep(3)

        except Exception as e:
            print(f"  [FAILED] {e}")
            stats["errors"].append(pdf_name)
            stats["by_pdf"][pdf_name] = 0

    # Save combined
    combined_file = OUTPUT_DIR / "all_pdfs_gemini_ultra.json"
    with open(combined_file, "w", encoding="utf-8") as f:
        json.dump(all_events, f, ensure_ascii=False, indent=2)

    # Save stats
    stats_file = OUTPUT_DIR / "gemini_ultra_stats.json"
    with open(stats_file, "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)

    print("\n" + "="*70)
    print("GEMINI ULTRA EXTRACTION COMPLETE")
    print("="*70)
    print(f"PDFs processed: {stats['processed']}/{len(all_pdfs)}")
    print(f"Total events: {stats['total_events']}")
    print(f"Average per PDF: {stats['total_events'] / max(stats['processed'], 1):.1f}")

    print(f"\nTop performers:")
    sorted_pdfs = sorted(stats['by_pdf'].items(), key=lambda x: -x[1])[:10]
    for pdf, count in sorted_pdfs:
        print(f"  {pdf:25s} {count:4d} events")

    if stats['errors']:
        print(f"\nErrors: {len(stats['errors'])}")
        for err in stats['errors']:
            print(f"  - {err}")

    return all_events, stats


if __name__ == "__main__":
    print("CMSD - ULTRA EXTRACTION with Gemini 2.5 Flash")
    print("Target: Maximum possible events from ALL 19 PDFs!")
    print()

    events, stats = extract_all_pdfs()

    print(f"\n[SUCCESS] {len(events)} events extracted!")
    print("Check data/processed/gemini_ultra/")
