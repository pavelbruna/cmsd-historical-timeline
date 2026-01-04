#!/usr/bin/env python3
"""
CMSD - DEEP EXTRACTION with Claude Sonnet 4.5 Vision
Claude Vision has MUCH BETTER OCR for Czech text than GPT-4o!
"""

import os
import json
import base64
from pathlib import Path
from typing import List, Dict, Any
import anthropic
import fitz  # PyMuPDF
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

    # Claude API limit: 5MB
    # Start with reasonable size
    max_size = (2048, 2048)
    img.thumbnail(max_size, Image.Resampling.LANCZOS)

    # Compress to JPEG for smaller size, then back to PNG if needed
    buffer = io.BytesIO()

    # Try PNG first with high compression
    img.save(buffer, format='PNG', optimize=True, compress_level=9)
    img_bytes = buffer.getvalue()

    # If still > 4.5MB, convert to JPEG for better compression
    if len(img_bytes) > 4.5 * 1024 * 1024:
        buffer = io.BytesIO()
        # Convert to RGB if needed (JPEG doesn't support transparency)
        if img.mode in ('RGBA', 'LA', 'P'):
            img = img.convert('RGB')
        img.save(buffer, format='JPEG', quality=85, optimize=True)
        img_bytes = buffer.getvalue()

    # If STILL too large, reduce size more
    while len(img_bytes) > 4.5 * 1024 * 1024:
        max_size = (max_size[0] * 0.8, max_size[1] * 0.8)
        img.thumbnail((int(max_size[0]), int(max_size[1])), Image.Resampling.LANCZOS)
        buffer = io.BytesIO()
        if img.mode in ('RGBA', 'LA', 'P'):
            img = img.convert('RGB')
        img.save(buffer, format='JPEG', quality=80, optimize=True)
        img_bytes = buffer.getvalue()

    img_base64 = base64.b64encode(img_bytes).decode('utf-8')

    doc.close()

    print(f"  Image: {len(img_bytes) / 1024 / 1024:.2f} MB (< 5MB limit)")
    return img_base64


def claude_deep_extraction(client: anthropic.Anthropic, image_base64: str, pdf_name: str) -> List[Dict[str, Any]]:
    """Deep extraction using Claude Sonnet 4.5 Vision - BEST for Czech OCR!"""
    print(f"DEEP extraction from {pdf_name} using Claude Vision...")

    prompt = f"""Analyzuješ HUSTOU českou historickou infografiku/časovou osu. Tato JEDNA stránka obsahuje 50-200+ historických událostí!

TVŮJ ÚKOL: Extrahuj KAŽDOU JEDNU historickou informaci kterou vidíš:

ČTI VŠECHNO:
- Velké nadpisy
- Malý text
- Drobné štítky
- Datumy na časové ose
- Jména u portrétů
- Názvy bitev
- Jména dynastií
- Značky roků
- Označení století
- Názvy období
- Geografické regiony
- Všechna čísla která vypadají jako roky
- Text v boxech, bublinách, tabulkách
- Popisky pod obrázky
- VŠECHNY viditelné historické události

OČEKÁVANÝ VÝSTUP: 50-200+ událostí z této JEDNÉ stránky!

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

KRITICKÁ PRAVIDLA:
✓ Extrahuj MINIMÁLNĚ 30-50 událostí (toto je hustá infografika!)
✓ Zahrň i drobné detaily (značky roků, malé štítky)
✓ Zachovej VŠECHNY české znaky (č, š, ž, ř, ů, ě, ý, á, í, ú)
✓ př.n.l./BC = záporný rok (-500)
✓ n.l./AD = kladný rok (1500)
✓ Pokud vidíš jen rok bez události, vytvoř událost "Rok XXXX"
✓ Přečti VŠECHEN viditelný text - nic nepřeskakuj!

PŘÍKLAD - extrahuj TOLIK detailů:
[
  {{
    "year": -4000,
    "year_end": -3000,
    "title": "Neolitická revoluce",
    "description": "Začátek zemědělství a domestikace zvířat v Blízkém východě. Přechod od lovu a sběru k usedlému způsobu života.",
    "category": "culture",
    "region": "Blízký východ",
    "importance": 5,
    "tags": ["neolit", "zemědělství", "revoluce"],
    "people": [],
    "places": ["Blízký východ"],
    "bible_refs": [],
    "source_page": "{pdf_name}"
  }},
  {{
    "year": -3500,
    "year_end": null,
    "title": "Vynález kola",
    "description": "První použití kola v Mezopotámii pro dopravu a hrnčířský kruh. Zásadní technologický pokrok.",
    "category": "discovery",
    "region": "Mezopotámie",
    "importance": 5,
    "tags": ["kolo", "vynález", "mezopotámie"],
    "people": [],
    "places": ["Mezopotámie"],
    "bible_refs": [],
    "source_page": "{pdf_name}"
  }},
  {{
    "year": -3000,
    "year_end": -2000,
    "title": "Bronzová doba",
    "description": "Období charakterizované používáním bronzu pro nástroje a zbraně. Rozvoj metalurgie a obchodu.",
    "category": "culture",
    "region": "Evropa",
    "importance": 4,
    "tags": ["bronz", "pravěk", "metalurgie"],
    "people": [],
    "places": ["Evropa"],
    "bible_refs": [],
    "source_page": "{pdf_name}"
  }}
]

Vrať POUZE validní JSON array s 30-200+ událostmi. ŽÁDNÝ jiný text!"""

    try:
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=16000,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/png",
                                "data": image_base64,
                            },
                        },
                        {
                            "type": "text",
                            "text": prompt
                        }
                    ],
                }
            ],
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
        print(f"  *** CLAUDE EXTRACTED {len(events)} EVENTS ***")
        return events

    except json.JSONDecodeError as e:
        print(f"  [ERROR] JSON parse: {e}")
        # Save for debugging
        with open(OUTPUT_DIR / f"{pdf_name}_claude_raw.txt", "w", encoding="utf-8") as f:
            f.write(response_text)
        print(f"  Raw response saved to {pdf_name}_claude_raw.txt")
        return []
    except Exception as e:
        print(f"  [ERROR] API: {e}")
        return []


def deep_extract_with_claude():
    """Deep extract from 9 best PDFs using Claude Vision"""
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY environment variable not set!")

    client = anthropic.Anthropic(api_key=api_key)

    # PDFs that showed some success in previous runs
    best_pdfs = [
        "1R.pdf",   # Had 13 events - expect 50-100
        "4R.pdf",   # Had 10 events - expect 40-80
        "7R.pdf",   # Had 11 events - expect 50-100
        "2R.pdf",   # Had 3 events - expect 30-60
        "3R.pdf",   # Had 4 events - expect 30-60
        "5R.pdf",   # Had 5 events - expect 40-80
        "6R.pdf",   # Had 9 events - expect 40-80
        "8R.pdf",   # Had 5 events - expect 40-80
        "zadniPredsRub.pdf"  # Had 5 events - expect 20-40
    ]

    all_events = []
    stats = {"processed": 0, "total_events": 0, "by_pdf": {}}

    for pdf_name in best_pdfs:
        pdf_path = PDFS_DIR / pdf_name

        if not pdf_path.exists():
            print(f"[SKIP] {pdf_name} not found")
            continue

        try:
            print(f"\n{'='*70}")
            print(f"DEEP EXTRACTION: {pdf_name}")
            print(f"{'='*70}")

            # Convert to optimized image (< 5MB for Claude)
            img_base64 = pdf_to_base64_image(pdf_path, dpi=150)

            # Extract with Claude Vision
            events = claude_deep_extraction(client, img_base64, pdf_path.stem)

            all_events.extend(events)
            stats["processed"] += 1
            stats["total_events"] += len(events)
            stats["by_pdf"][pdf_name] = len(events)

            # Save per-PDF
            output_file = OUTPUT_DIR / f"{pdf_path.stem}_claude_deep.json"
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(events, f, ensure_ascii=False, indent=2)

            print(f"[SAVED] {output_file.name} ({len(events)} events)")

        except Exception as e:
            print(f"[ERROR] {pdf_name}: {e}")
            stats["by_pdf"][pdf_name] = 0

    # Save combined
    combined = OUTPUT_DIR / "claude_deep_extraction.json"
    with open(combined, "w", encoding="utf-8") as f:
        json.dump(all_events, f, ensure_ascii=False, indent=2)

    # Save stats
    stats_file = OUTPUT_DIR / "claude_extraction_stats.json"
    with open(stats_file, "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)

    print(f"\n{'='*70}")
    print(f"CLAUDE DEEP EXTRACTION COMPLETE")
    print(f"{'='*70}")
    print(f"PDFs processed: {stats['processed']}/9")
    print(f"Total events: {stats['total_events']}")
    print(f"Average per PDF: {stats['total_events'] / max(stats['processed'], 1):.1f}")
    print(f"\nBreakdown:")
    for pdf, count in stats['by_pdf'].items():
        print(f"  {pdf:20s} {count:4d} events")

    return all_events, stats


if __name__ == "__main__":
    print("CMSD - DEEP EXTRACTION with Claude Sonnet 4.5 Vision")
    print("=" * 70)
    print("Claude Vision = BEST OCR for Czech historical infographics!")
    print("Target: 40-80+ events PER PDF = 400-700 total")
    print()

    events, stats = deep_extract_with_claude()

    print("\n[SUCCESS] Check data/processed/claude_deep_extraction.json")
