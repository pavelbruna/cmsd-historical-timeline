#!/usr/bin/env python3
"""
CMSD Historical Timeline Data Extraction Pipeline - IMPROVED VERSION
Enhanced prompt and settings for dense Czech historical infographics
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

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def pdf_to_base64_image(pdf_path: Path, dpi: int = 200) -> str:
    """Convert PDF to high-res base64 image"""
    print(f"Converting {pdf_path.name} to image (DPI: {dpi})...")

    doc = fitz.open(str(pdf_path))
    page = doc[0]

    # Higher resolution for better text recognition
    zoom = dpi / 72
    mat = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat)

    img_data = pix.tobytes("png")
    img = Image.open(io.BytesIO(img_data))

    # Resize if too large
    max_size = (2500, 2500)
    img.thumbnail(max_size, Image.Resampling.LANCZOS)

    buffer = io.BytesIO()
    img.save(buffer, format='PNG', optimize=True)
    img_bytes = buffer.getvalue()
    img_base64 = base64.b64encode(img_bytes).decode('utf-8')

    doc.close()

    print(f"  Image size: {len(img_bytes) / 1024 / 1024:.2f} MB")
    return img_base64


def extract_events_from_image(client: OpenAI, image_base64: str, pdf_name: str) -> List[Dict[str, Any]]:
    """Extract ALL events from Czech historical infographic using improved prompt"""
    print(f"Extracting events from {pdf_name} with improved prompt...")

    prompt = f"""Toto je ČESKÁ HISTORICKÁ INFOGRAFIKA/ČASOVÁ OSA s DESÍTKAMI až STOVKAMI historických událostí.

TVŮJ ÚKOL: Extrahuj ÚPLNĚ VŠECHNY historické události, které vidíš v této infografice. Zahrnuje to:

1. HLAVNÍ UDÁLOSTI s velkým textem
2. VEDLEJŠÍ UDÁLOSTI s menším textem
3. DATUMY a ROKY na časové ose
4. POPISKY u obrázků a ikon
5. VŠECHNY HISTORICKÉ MILNÍKY ať už jsou velké nebo malé
6. JMÉNA PANOVNÍKŮ, BITEV, OBJEVŮ, VYNÁLEZŮ
7. TEXT v BUBLINÁCH, BOXECH, TABULKÁCH

OČEKÁVANÝ VÝSTUP: 20-100+ událostí na stránku (infografiky jsou VELMI HUSTÉ!)

Pro KAŽDOU událost vytvoř JSON objekt:

{{
  "year": ROK (záporný = př.n.l., kladný = n.l.),
  "year_end": KONEC_OBDOBÍ nebo null,
  "title": "Stručný název události",
  "description": "Detailní popis co se stalo a proč je to důležité",
  "category": "religion/war/politics/discovery/culture/science/economics",
  "region": "Geografická oblast",
  "importance": 1-5 (5=klíčová světová událost, 1=menší zmínka),
  "tags": ["klíčová", "slova"],
  "people": ["Jména osob"],
  "places": ["Názvy míst"],
  "bible_refs": ["Biblické odkazy pokud jsou"],
  "source_page": "{pdf_name}"
}}

KRITICKÁ PRAVIDLA:
✓ Zachovej VŠECHNY české znaky (č, š, ž, ř, ů, ě, ý, á, í, ú, ó)
✓ Extrahuj i MALÉ události (důležité jsou všechny detaily!)
✓ Roky př.n.l. = záporné číslo (-2348)
✓ Roky n.l. = kladné číslo (1492)
✓ Pokud vidíš období, použij year + year_end
✓ Pokud vidíš jen rok bez události, přidej ho jako "Rok XXXX"
✓ NEPRESKAKUJ nic - každý text v infografice je důležitý!

PŘÍKLAD VÝSTUPU (minimálně 20+ událostí!):
```json
[
  {{
    "year": -3000,
    "year_end": -2000,
    "title": "Bronzová doba v Evropě",
    "description": "Období charakterizované používáním bronzu pro nástroje a zbraně. Rozvoj obchodu a řemesel.",
    "category": "culture",
    "region": "Evropa",
    "importance": 4,
    "tags": ["bronz", "pravěk", "technologie"],
    "people": [],
    "places": ["Evropa"],
    "bible_refs": [],
    "source_page": "{pdf_name}"
  }},
  {{
    "year": -2348,
    "year_end": null,
    "title": "Potopa světa",
    "description": "Biblická potopa za Noeho. Globální katastrofa podle knihy Genesis.",
    "category": "religion",
    "region": "Blízký východ",
    "importance": 5,
    "tags": ["bible", "potopa", "noe"],
    "people": ["Noe"],
    "places": ["Ararat"],
    "bible_refs": ["Genesis 6-9"],
    "source_page": "{pdf_name}"
  }}
]
```

DŮLEŽITÉ: Vrať POUZE validní JSON array. Žádný další text, žádné markdown kód bloky, jen čistý JSON!

Začni extrakci VŠECH událostí z infografiky:"""

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
            max_tokens=16000,  # INCREASED!
            temperature=0  # Consistency
        )

        response_text = response.choices[0].message.content.strip()

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
        print(f"  [SUCCESS] Extracted {len(events)} events")
        return events

    except json.JSONDecodeError as e:
        print(f"  [ERROR] JSON parse failed: {e}")
        print(f"  Response: {response_text[:300]}...")
        return []
    except Exception as e:
        print(f"  [ERROR] API error: {e}")
        return []


def reprocess_failed_pdfs(pdfs_to_process: List[str]):
    """Re-process specific PDFs with improved extraction"""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY not set")

    client = OpenAI(api_key=api_key)

    all_events = []
    stats = {
        "total_pdfs": len(pdfs_to_process),
        "processed_pdfs": 0,
        "total_events": 0,
        "errors": []
    }

    for pdf_name in pdfs_to_process:
        pdf_path = PDFS_DIR / pdf_name

        if not pdf_path.exists():
            print(f"[SKIP] {pdf_name} not found")
            continue

        try:
            print(f"\n{'='*60}")
            print(f"Re-processing: {pdf_name}")
            print(f"{'='*60}")

            # Convert to image
            img_base64 = pdf_to_base64_image(pdf_path, dpi=200)

            # Extract with improved prompt
            events = extract_events_from_image(client, img_base64, pdf_path.stem)

            all_events.extend(events)
            stats["processed_pdfs"] += 1
            stats["total_events"] += len(events)

            # Save per-PDF result
            output_file = OUTPUT_DIR / f"{pdf_path.stem}_events_v2.json"
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(events, f, ensure_ascii=False, indent=2)

            print(f"[OK] Saved {len(events)} events to {output_file.name}")

        except Exception as e:
            error_msg = f"Error: {pdf_name}: {str(e)}"
            print(f"[ERROR] {error_msg}")
            stats["errors"].append(error_msg)

    # Save combined v2 results
    combined_file = OUTPUT_DIR / "reprocessed_events.json"
    with open(combined_file, "w", encoding="utf-8") as f:
        json.dump(all_events, f, ensure_ascii=False, indent=2)

    print(f"\n{'='*60}")
    print(f"RE-PROCESSING COMPLETE")
    print(f"{'='*60}")
    print(f"PDFs processed: {stats['processed_pdfs']}/{stats['total_pdfs']}")
    print(f"NEW events extracted: {stats['total_events']}")
    print(f"Errors: {len(stats['errors'])}")

    return all_events, stats


if __name__ == "__main__":
    # PDFs to re-process (empty + low count)
    failed_pdfs = [
        "1L.pdf", "2L.pdf", "2R.pdf", "3L.pdf", "3R.pdf", "4L.pdf",
        "5L.pdf", "5R.pdf", "6L.pdf", "6R.pdf", "7L.pdf", "8L.pdf",
        "8R.pdf", "PredniPreds.pdf", "zadniPredsLic.pdf", "zadniPredsRub.pdf"
    ]

    print("CMSD - IMPROVED EXTRACTION (v2)")
    print("=" * 60)
    print(f"Re-processing {len(failed_pdfs)} PDFs with:")
    print("  - Enhanced prompt for dense infographics")
    print("  - max_tokens: 16000 (was 4096)")
    print("  - DPI: 200 (was 150)")
    print("  - temperature: 0 (consistency)")
    print()

    events, stats = reprocess_failed_pdfs(failed_pdfs)

    print("\n[DONE] Check data/processed/reprocessed_events.json")
