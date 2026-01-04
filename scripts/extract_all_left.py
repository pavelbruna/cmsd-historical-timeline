#!/usr/bin/env python3
"""
CMSD - Extract ALL Left Pages
Process all 8 Left pages to maximize data extraction
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
import time

PROJECT_ROOT = Path(__file__).parent.parent
PDFS_DIR = PROJECT_ROOT / "data" / "raw" / "pdfs"
OUTPUT_DIR = PROJECT_ROOT / "data" / "processed"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def pdf_to_base64_image(pdf_path: Path, dpi: int = 150) -> str:
    """Convert PDF to optimized image (< 5MB for Claude API)"""
    doc = fitz.open(str(pdf_path))
    page = doc[0]

    zoom = dpi / 72
    mat = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat)

    img_data = pix.tobytes("png")
    img = Image.open(io.BytesIO(img_data))

    # Target: 3.7 MB raw = ~5 MB base64
    target_size = 3.7 * 1024 * 1024

    # Aggressive JPEG compression
    max_size = (2048, 2048)
    img.thumbnail(max_size, Image.Resampling.LANCZOS)

    buffer = io.BytesIO()
    if img.mode in ('RGBA', 'LA', 'P'):
        img = img.convert('RGB')
    img.save(buffer, format='JPEG', quality=75, optimize=True)
    img_bytes = buffer.getvalue()

    # Auto-resize loop
    while len(img_bytes) > target_size:
        max_size = (int(max_size[0] * 0.85), int(max_size[1] * 0.85))
        img.thumbnail(max_size, Image.Resampling.LANCZOS)
        buffer = io.BytesIO()
        img.save(buffer, format='JPEG', quality=70, optimize=True)
        img_bytes = buffer.getvalue()

    img_base64 = base64.b64encode(img_bytes).decode('utf-8')
    doc.close()

    base64_size_mb = len(img_base64.encode('utf-8')) / 1024 / 1024
    print(f"  Image: {len(img_bytes) / 1024 / 1024:.2f} MB (base64: {base64_size_mb:.2f} MB)")
    return img_base64


def extract_single_pdf(client: anthropic.Anthropic, image_base64: str, pdf_name: str) -> List[Dict[str, Any]]:
    """Extract from single PDF using Claude Vision"""
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

Vrať POUZE validní JSON array:"""

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
        print(f"  [OK] {len(events)} events")
        return events

    except Exception as e:
        print(f"  [ERROR] {e}")
        return []


def extract_all_left_pages():
    """Extract from all Left pages"""
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("[ERROR] ANTHROPIC_API_KEY not set!")
        return

    client = anthropic.Anthropic(api_key=api_key)

    # All Left pages (skip 1L - already done)
    left_pages = ["2L.pdf", "3L.pdf", "4L.pdf", "5L.pdf", "6L.pdf", "7L.pdf", "8L.pdf"]

    all_events = []
    stats = {"processed": 0, "total_events": 0, "by_pdf": {}}

    for pdf_name in left_pages:
        pdf_path = PDFS_DIR / pdf_name

        if not pdf_path.exists():
            print(f"[SKIP] {pdf_name} not found")
            continue

        try:
            print(f"\n{'='*70}")
            print(f"EXTRACTING: {pdf_name}")
            print(f"{'='*70}")

            # Convert
            img_base64 = pdf_to_base64_image(pdf_path, dpi=150)

            # Extract
            events = extract_single_pdf(client, img_base64, pdf_path.stem)

            all_events.extend(events)
            stats["processed"] += 1
            stats["total_events"] += len(events)
            stats["by_pdf"][pdf_name] = len(events)

            # Save per-PDF
            output_file = OUTPUT_DIR / f"{pdf_path.stem}_left.json"
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(events, f, ensure_ascii=False, indent=2)

            print(f"  [SAVED] {output_file.name}")

            # Rate limit: wait 2 seconds between requests
            if pdf_name != left_pages[-1]:
                print("  Waiting 2s (rate limit)...")
                time.sleep(2)

        except Exception as e:
            print(f"[ERROR] {pdf_name}: {e}")
            stats["by_pdf"][pdf_name] = 0

    # Save combined
    combined_file = OUTPUT_DIR / "all_left_pages.json"
    with open(combined_file, "w", encoding="utf-8") as f:
        json.dump(all_events, f, ensure_ascii=False, indent=2)

    # Save stats
    stats_file = OUTPUT_DIR / "left_pages_stats.json"
    with open(stats_file, "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)

    print(f"\n{'='*70}")
    print("LEFT PAGES EXTRACTION COMPLETE")
    print(f"{'='*70}")
    print(f"PDFs processed: {stats['processed']}/7")
    print(f"Total events: {stats['total_events']}")
    print(f"Average per PDF: {stats['total_events'] / max(stats['processed'], 1):.1f}")
    print(f"\nBreakdown:")
    for pdf, count in stats['by_pdf'].items():
        print(f"  {pdf:15s} {count:4d} events")

    return all_events, stats


if __name__ == "__main__":
    print("CMSD - Extract ALL Left Pages")
    print("="*70)
    events, stats = extract_all_left_pages()
    print(f"\n[SUCCESS] {len(events)} events from Left pages!")
