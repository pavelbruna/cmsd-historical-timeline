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
from openai import OpenAI
import fitz  # PyMuPDF
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
    Convert PDF to base64-encoded image for Vision API using PyMuPDF
    """
    print(f"Converting {pdf_path.name} to image...")

    # Open PDF
    doc = fitz.open(str(pdf_path))

    # Get first page
    page = doc[0]

    # Render page to pixmap (image)
    zoom = dpi / 72  # 72 DPI is default
    mat = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat)

    # Convert to PIL Image
    img_data = pix.tobytes("png")
    img = Image.open(io.BytesIO(img_data))

    # Resize if too large (max 20MB for OpenAI API)
    max_size = (2000, 2000)
    img.thumbnail(max_size, Image.Resampling.LANCZOS)

    # Convert to base64
    buffer = io.BytesIO()
    img.save(buffer, format='PNG', optimize=True)
    img_bytes = buffer.getvalue()
    img_base64 = base64.b64encode(img_bytes).decode('utf-8')

    doc.close()

    print(f"  Image size: {len(img_bytes) / 1024 / 1024:.2f} MB")

    return img_base64


def extract_events_from_image(client: OpenAI, image_base64: str, pdf_name: str) -> List[Dict[str, Any]]:
    """
    Extract structured historical events from image using GPT-4o Vision
    """
    print(f"Extracting events from {pdf_name}...")

    prompt = f"""Analyzuj tento cesky historicky dokument/infografiku a extrahuj VSECHNY historicke udalosti.

Pro KAZDOU udalost, kterou vidis v dokumentu, vytvor zaznam s temito udaji:
- year: rok (zaporne cislo pro pr.n.l./BC, napr. -608, kladne pro n.l./AD, napr. 1492)
- year_end: konec obdobi (pokud je to obdobi, jinak null)
- title: kratky nazev udalosti (max 100 znaku)
- description: detailni popis (2-3 vety)
- category: kategorie (religion/war/politics/discovery/culture/science)
- region: geograficka oblast (napr. "Blizky vychod", "Evropa", "Asie")
- importance: dulezitost 1-5 (5 = nejvyssi)
- tags: klicova slova (seznam)
- people: zminene osoby (seznam jmen)
- places: zminena mista (seznam nazvu)
- bible_refs: biblicke odkazy pokud jsou (seznam, napr. ["Daniel 7:4"])
- source_page: "{pdf_name}"

DULEZITE:
- Zachovej VSECHNY ceske znaky (c, s, z, r, u, e, y, a, i)
- Roky pr.n.l. = zaporne cislo (napr. 608 pr.n.l. = -608)
- Roky n.l. = kladne cislo (napr. 1492 n.l. = 1492)
- Extrahuj VSECHNY udalosti ktere vidis, i mensi zmínky
- Pokud vidis casove obdobi, pouzij year + year_end

Vrat vysledek jako JSON array udalosti:
```json
[
  {{
    "year": -608,
    "year_end": -538,
    "title": "Babylonska rise",
    "description": "...",
    "category": "politics",
    "region": "Blizky vychod",
    "importance": 5,
    "tags": ["babylon", "rise", "nabuchodonosor"],
    "people": ["Nabuchodonozor"],
    "places": ["Babylon"],
    "bible_refs": ["Daniel 7:4"],
    "source_page": "{pdf_name}"
  }}
]
```

Vrat POUZE cisty JSON array, zadny dalsi text."""

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": prompt
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{image_base64}",
                                "detail": "high"
                            }
                        }
                    ],
                }
            ],
            max_tokens=4096,
            temperature=0.1
        )

        # Extract JSON from response
        response_text = response.choices[0].message.content.strip()

        # Remove markdown code blocks if present
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
        print(f"  [ERROR] JSON parsing error: {e}")
        print(f"  Response preview: {response_text[:500]}")
        return []
    except Exception as e:
        print(f"  [ERROR] API error: {e}")
        return []


def process_all_pdfs():
    """
    Process all PDFs and extract events
    """
    # Get API key from environment
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable not set")

    client = OpenAI(api_key=api_key)

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

            print(f"[OK] Saved to {output_file.name}")

        except Exception as e:
            error_msg = f"Error processing {pdf_path.name}: {str(e)}"
            print(f"[ERROR] {error_msg}")
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

    print("\n[OK] Done!")
