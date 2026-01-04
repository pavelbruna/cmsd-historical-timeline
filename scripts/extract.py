#!/usr/bin/env python3
"""
CMSD Historical Timeline Data Extraction Pipeline
Extracts structured historical events from PDF infographics using Vision AI
"""

import os
import json
import base64
from pathlib import Path
from typing import List, Dict, Any
import anthropic
from pdf2image import convert_from_path
from PIL import Image
import io

# Configuration
PROJECT_ROOT = Path(__file__).parent.parent
PDFS_DIR = PROJECT_ROOT / "data" / "raw" / "pdfs"
OUTPUT_DIR = PROJECT_ROOT / "data" / "processed"
TEMP_DIR = PROJECT_ROOT / "temp"

# Create directories
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
TEMP_DIR.mkdir(parents=True, exist_ok=True)


def pdf_to_base64_image(pdf_path: Path, dpi: int = 150) -> str:
    """
    Convert PDF to base64-encoded image for Vision API
    """
    print(f"Converting {pdf_path.name} to image...")

    # Convert PDF to images (typically just 1 page per PDF)
    images = convert_from_path(str(pdf_path), dpi=dpi, first_page=1, last_page=1)

    if not images:
        raise ValueError(f"Could not convert {pdf_path.name} to image")

    # Get first page
    img = images[0]

    # Resize if too large (max 5MB for API)
    max_size = (2000, 2000)
    img.thumbnail(max_size, Image.Resampling.LANCZOS)

    # Convert to base64
    buffer = io.BytesIO()
    img.save(buffer, format='PNG', optimize=True)
    img_bytes = buffer.getvalue()
    img_base64 = base64.b64encode(img_bytes).decode('utf-8')

    print(f"  Image size: {len(img_bytes) / 1024 / 1024:.2f} MB")

    return img_base64


def extract_events_from_image(client: anthropic.Anthropic, image_base64: str, pdf_name: str) -> List[Dict[str, Any]]:
    """
    Extract structured historical events from image using Claude Vision
    """
    print(f"Extracting events from {pdf_name}...")

    prompt = f"""Analyzuj tento český historický dokument/infografiku a extrahuj VŠECHNY historické události.

Pro KAŽDOU událost, kterou vidíš v dokumentu, vytvoř záznam s těmito údaji:
- year: rok (záporné číslo pro př.n.l./BC, např. -608, kladné pro n.l./AD, např. 1492)
- year_end: konec období (pokud je to období, jinak null)
- title: krátký název události (max 100 znaků)
- description: detailní popis (2-3 věty)
- category: kategorie (religion/war/politics/discovery/culture/science)
- region: geografická oblast (např. "Blízký východ", "Evropa", "Asie")
- importance: důležitost 1-5 (5 = nejvyšší)
- tags: klíčová slova (seznam)
- people: zmíněné osoby (seznam jmen)
- places: zmíněná místa (seznam názvů)
- bible_refs: biblické odkazy pokud jsou (seznam, např. ["Daniel 7:4"])
- source_page: "{pdf_name}"

DŮLEŽITÉ:
- Zachovej VŠECHNY české znaky (č, š, ž, ř, ů, ě, ý, á, í)
- Roky př.n.l. = záporné číslo (např. 608 př.n.l. = -608)
- Roky n.l. = kladné číslo (např. 1492 n.l. = 1492)
- Extrahuj VŠECHNY události které vidíš, i menší zmínky
- Pokud vidíš časové období, použij year + year_end

Vrať výsledek jako JSON array událostí:
```json
[
  {{
    "year": -608,
    "year_end": -538,
    "title": "Babylónská říše",
    "description": "...",
    "category": "politics",
    "region": "Blízký východ",
    "importance": 5,
    "tags": ["babylon", "říše", "nabuchodonosor"],
    "people": ["Nabuchodonozor"],
    "places": ["Babylón"],
    "bible_refs": ["Daniel 7:4"],
    "source_page": "{pdf_name}"
  }}
]
```

Vrať POUZE čistý JSON array, žádný další text."""

    message = client.messages.create(
        model="claude-sonnet-4-5-20250929",
        max_tokens=4096,
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

    # Extract JSON from response
    response_text = message.content[0].text.strip()

    # Remove markdown code blocks if present
    if response_text.startswith("```json"):
        response_text = response_text[7:]
    if response_text.startswith("```"):
        response_text = response_text[3:]
    if response_text.endswith("```"):
        response_text = response_text[:-3]

    response_text = response_text.strip()

    # Parse JSON
    try:
        events = json.loads(response_text)
        print(f"  ✓ Extracted {len(events)} events")
        return events
    except json.JSONDecodeError as e:
        print(f"  ✗ JSON parsing error: {e}")
        print(f"  Response preview: {response_text[:500]}")
        return []


def process_all_pdfs():
    """
    Process all PDFs and extract events
    """
    # Get API key from environment
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY environment variable not set")

    client = anthropic.Anthropic(api_key=api_key)

    # Get all PDFs sorted by name
    pdf_files = sorted(PDFS_DIR.glob("*.pdf"))

    print(f"\nFound {len(pdf_files)} PDF files to process\n")

    all_events = []
    stats = {
        "total_pdfs": len(pdf_files),
        "processed_pdfs": 0,
        "total_events": 0,
        "errors": []
    }

    for pdf_path in pdf_files:
        try:
            print(f"\n{'='*60}")
            print(f"Processing: {pdf_path.name}")
            print(f"{'='*60}")

            # Convert PDF to image
            img_base64 = pdf_to_base64_image(pdf_path)

            # Extract events
            events = extract_events_from_image(client, img_base64, pdf_path.stem)

            # Add to collection
            all_events.extend(events)
            stats["processed_pdfs"] += 1
            stats["total_events"] += len(events)

            # Save intermediate results
            output_file = OUTPUT_DIR / f"{pdf_path.stem}_events.json"
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(events, f, ensure_ascii=False, indent=2)

            print(f"✓ Saved to {output_file.name}")

        except Exception as e:
            error_msg = f"Error processing {pdf_path.name}: {str(e)}"
            print(f"✗ {error_msg}")
            stats["errors"].append(error_msg)

    # Save combined results
    combined_file = OUTPUT_DIR / "all_events.json"
    with open(combined_file, "w", encoding="utf-8") as f:
        json.dump(all_events, f, ensure_ascii=False, indent=2)

    print(f"\n{'='*60}")
    print(f"EXTRACTION COMPLETE")
    print(f"{'='*60}")
    print(f"Total PDFs: {stats['total_pdfs']}")
    print(f"Processed: {stats['processed_pdfs']}")
    print(f"Total events extracted: {stats['total_events']}")
    print(f"Errors: {len(stats['errors'])}")
    print(f"\nCombined results saved to: {combined_file}")

    # Save stats
    stats_file = OUTPUT_DIR / "extraction_stats.json"
    with open(stats_file, "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)

    return all_events, stats


if __name__ == "__main__":
    print("CMSD Historical Timeline Data Extraction")
    print("=" * 60)

    events, stats = process_all_pdfs()

    print("\n✓ Done!")
