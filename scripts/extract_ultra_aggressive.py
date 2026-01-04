#!/usr/bin/env python3
"""
CMSD - ULTRA AGGRESSIVE MULTI-PASS EXTRACTION
Extract MAXIMUM possible data using multiple passes + knowledge cards

Strategy:
1. PASS 1: Main events (what we did before)
2. PASS 2: Micro details (years, labels, small text, between-events)
3. BONUS: Knowledge cards integration

Target: 500-700+ events!
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
KNOWLEDGE_DIR = PROJECT_ROOT / "data" / "raw" / "knowledge_cards"
OUTPUT_DIR = PROJECT_ROOT / "data" / "processed"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def pdf_to_base64_image(pdf_path: Path) -> str:
    """Convert PDF to optimized image"""
    doc = fitz.open(str(pdf_path))
    page = doc[0]

    zoom = 150 / 72
    mat = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat)

    img_data = pix.tobytes("png")
    img = Image.open(io.BytesIO(img_data))

    max_size = (2048, 2048)
    img.thumbnail(max_size, Image.Resampling.LANCZOS)

    buffer = io.BytesIO()
    img.save(buffer, format='PNG', optimize=True, compress_level=9)
    img_bytes = buffer.getvalue()

    if len(img_bytes) > 4.5 * 1024 * 1024:
        buffer = io.BytesIO()
        if img.mode in ('RGBA', 'LA', 'P'):
            img = img.convert('RGB')
        img.save(buffer, format='JPEG', quality=85, optimize=True)
        img_bytes = buffer.getvalue()

    while len(img_bytes) > 4.5 * 1024 * 1024:
        max_size = (int(max_size[0] * 0.8), int(max_size[1] * 0.8))
        img.thumbnail(max_size, Image.Resampling.LANCZOS)
        buffer = io.BytesIO()
        if img.mode in ('RGBA', 'LA', 'P'):
            img = img.convert('RGB')
        img.save(buffer, format='JPEG', quality=80, optimize=True)
        img_bytes = buffer.getvalue()

    img_base64 = base64.b64encode(img_bytes).decode('utf-8')
    doc.close()

    return img_base64


def pass1_main_events(client: anthropic.Anthropic, image_base64: str, pdf_name: str) -> List[Dict[str, Any]]:
    """PASS 1: Extract main historical events"""
    print(f"  PASS 1: Main events...")

    prompt = f"""ČESKÁ HISTORICKÁ INFOGRAFIKA - PASS 1: HLAVNÍ UDÁLOSTI

Extrahuj VŠECHNY HLAVNÍ historické události z této infografiky.

ZAMĚŘ SE NA:
- Velké nadpisy a titulky
- Významné historické milníky
- Války, bitvy, revoluce
- Období vlády panovníků
- Důležité objevy a vynálezy
- Významné kulturní události
- Biblické události

Očekávaný počet: 40-80 událostí

Pro každou událost vytvoř JSON:
{{
  "year": ROK,
  "year_end": KONEC nebo null,
  "title": "Název události",
  "description": "Detailní popis",
  "category": "religion/war/politics/discovery/culture/science/economics",
  "region": "Geografická oblast",
  "importance": 1-5,
  "tags": ["tagy"],
  "people": ["Osoby"],
  "places": ["Místa"],
  "bible_refs": ["Bible odkazy"],
  "source_page": "{pdf_name}",
  "extraction_pass": "pass1_main"
}}

PRAVIDLA:
✓ Všechny české znaky (č, š, ž, ř, ů, ě, ý, á, í)
✓ př.n.l. = záporný rok, n.l. = kladný rok
✓ Extrahuj i menší události, ne jen ty největší!

Vrať POUZE JSON array:"""

    try:
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=16000,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": image_base64}},
                    {"type": "text", "text": prompt}
                ],
            }],
        )

        response_text = message.content[0].text.strip()
        if response_text.startswith("```json"): response_text = response_text[7:]
        if response_text.startswith("```"): response_text = response_text[3:]
        if response_text.endswith("```"): response_text = response_text[:-3]
        response_text = response_text.strip()

        events = json.loads(response_text)
        print(f"    [OK] PASS 1: {len(events)} main events")
        return events

    except Exception as e:
        print(f"    [ERROR] PASS 1: {e}")
        return []


def pass2_micro_details(client: anthropic.Anthropic, image_base64: str, pdf_name: str) -> List[Dict[str, Any]]:
    """PASS 2: Extract micro details, years, labels"""
    print(f"  PASS 2: Micro details...")

    prompt = f"""ČESKÁ HISTORICKÁ INFOGRAFIKA - PASS 2: MIKRO DETAILY

Teď extrahuj VŠECHNY DROBNÉ detaily které jsi možná v prvním průchodu přeskočil!

ZAMĚŘ SE NA:
- Jednotlivé ROKY na časové ose (i bez velkého popisu)
- Malé štítky a poznámky
- Jména panovníků u portétů
- Datumy bitev
- Názvy dynastií
- Období (století, epochy)
- Geografické regiony zmíněné v textu
- Drobné historické zmínky
- Text v boxech a bublinách
- Vedlejší události kolem hlavních

DŮLEŽITÉ: Extrahuj i události které vypadají "malé" - KAŽDÝ detail má hodnotu!

Očekávaný počet: 20-50+ detailů

Pro každou věc vytvoř JSON (stejná struktura jako Pass 1):
{{
  "year": ROK,
  "year_end": KONEC nebo null,
  "title": "Název (i když je to jen rok nebo jméno)",
  "description": "Co je to za událost nebo detail",
  "category": "politics/war/culture/etc",
  "region": "Oblast",
  "importance": 1-3 (drobné detaily = 1-2),
  "tags": ["tagy"],
  "people": ["Osoby pokud jsou"],
  "places": ["Místa pokud jsou"],
  "bible_refs": [],
  "source_page": "{pdf_name}",
  "extraction_pass": "pass2_micro"
}}

PŘÍKLADY CO EXTRAHOVAT:
- "1453" na časové ose → událost "Rok 1453"
- Malý portét s názvem → událost s tím jménem
- Epocha "Středověk 500-1500" → událost období
- Malá poznámka o bitvě → událost
- Geografický region "Persie" → zmínka v událostech

Vrať POUZE JSON array:"""

    try:
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=16000,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": image_base64}},
                    {"type": "text", "text": prompt}
                ],
            }],
        )

        response_text = message.content[0].text.strip()
        if response_text.startswith("```json"): response_text = response_text[7:]
        if response_text.startswith("```"): response_text = response_text[3:]
        if response_text.endswith("```"): response_text = response_text[:-3]
        response_text = response_text.strip()

        events = json.loads(response_text)
        print(f"    [OK] PASS 2: {len(events)} micro details")
        return events

    except Exception as e:
        print(f"    [ERROR] PASS 2: {e}")
        return []


def load_knowledge_cards() -> List[Dict[str, Any]]:
    """Load and convert knowledge cards to events"""
    print("\n" + "="*70)
    print("LOADING KNOWLEDGE CARDS")
    print("="*70)

    all_cards = []
    jsonl_files = sorted(KNOWLEDGE_DIR.glob("*.jsonl"))

    for jsonl_file in jsonl_files:
        with open(jsonl_file, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    card = json.loads(line)
                    all_cards.append(card)

    print(f"Loaded {len(all_cards)} knowledge cards from {len(jsonl_files)} files")

    # Convert cards to events
    events = []
    for card in all_cards:
        # Extract entities from card
        entities = card.get('entities', {})
        events_list = entities.get('events', [])
        people_list = entities.get('people', [])
        places_list = entities.get('places', [])

        # Create event from card if it has event data
        if events_list:
            for event_name in events_list:
                # Try to extract year from title or summary
                event = {
                    "year": None,  # Would need parsing
                    "year_end": None,
                    "title": event_name,
                    "description": card.get('summary', ''),
                    "category": "unknown",
                    "region": None,
                    "importance": 3,
                    "tags": card.get('topics', []),
                    "people": people_list,
                    "places": places_list,
                    "bible_refs": [],
                    "source_page": card.get('doc_id', 'knowledge_card'),
                    "extraction_pass": "knowledge_cards"
                }
                events.append(event)

    print(f"Converted {len(events)} events from knowledge cards")
    return events


def ultra_aggressive_extraction():
    """ULTRA AGGRESSIVE multi-pass extraction"""
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY not set")

    client = anthropic.Anthropic(api_key=api_key)

    # PDFs to process
    best_pdfs = [
        "1R.pdf", "2R.pdf", "3R.pdf", "4R.pdf",
        "5R.pdf", "6R.pdf", "7R.pdf", "8R.pdf",
        "zadniPredsRub.pdf"
    ]

    all_events = []
    stats = {
        "pdfs_processed": 0,
        "pass1_events": 0,
        "pass2_events": 0,
        "knowledge_events": 0,
        "total_before_dedup": 0,
        "by_pdf": {}
    }

    # MULTI-PASS EXTRACTION FROM PDFs
    for pdf_name in best_pdfs:
        pdf_path = PDFS_DIR / pdf_name
        if not pdf_path.exists():
            continue

        try:
            print(f"\n{'='*70}")
            print(f"ULTRA EXTRACTION: {pdf_name}")
            print(f"{'='*70}")

            img_base64 = pdf_to_base64_image(pdf_path)

            # PASS 1: Main events
            pass1_events = pass1_main_events(client, img_base64, pdf_path.stem)
            all_events.extend(pass1_events)
            stats["pass1_events"] += len(pass1_events)

            # PASS 2: Micro details
            pass2_events = pass2_micro_details(client, img_base64, pdf_path.stem)
            all_events.extend(pass2_events)
            stats["pass2_events"] += len(pass2_events)

            total_from_pdf = len(pass1_events) + len(pass2_events)
            stats["by_pdf"][pdf_name] = total_from_pdf
            stats["pdfs_processed"] += 1

            print(f"  TOTAL from {pdf_name}: {total_from_pdf} events")

            # Save per-PDF
            output_file = OUTPUT_DIR / f"{pdf_path.stem}_ultra.json"
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(pass1_events + pass2_events, f, ensure_ascii=False, indent=2)

        except Exception as e:
            print(f"[ERROR] {pdf_name}: {e}")

    # LOAD KNOWLEDGE CARDS
    try:
        knowledge_events = load_knowledge_cards()
        all_events.extend(knowledge_events)
        stats["knowledge_events"] = len(knowledge_events)
    except Exception as e:
        print(f"[ERROR] Knowledge cards: {e}")

    stats["total_before_dedup"] = len(all_events)

    # Save raw combined
    raw_combined = OUTPUT_DIR / "ultra_extraction_raw.json"
    with open(raw_combined, "w", encoding="utf-8") as f:
        json.dump(all_events, f, ensure_ascii=False, indent=2)

    # DEDUPLICATION
    print(f"\n{'='*70}")
    print("DEDUPLICATION")
    print(f"{'='*70}")
    print(f"Before dedup: {len(all_events)} events")

    seen = set()
    unique_events = []
    for event in all_events:
        # Skip events without year (from knowledge cards without parsed dates)
        if event.get('year') is None:
            continue

        key = (
            event.get('title', '').lower().strip(),
            event.get('year'),
            event.get('source_page', '')
        )

        if key not in seen:
            seen.add(key)
            unique_events.append(event)

    print(f"After dedup: {len(unique_events)} unique events")
    print(f"Duplicates removed: {len(all_events) - len(unique_events)}")

    # Sort by year
    unique_events.sort(key=lambda e: e.get('year', 0))

    # Save final
    final_file = OUTPUT_DIR / "ultra_extraction_final.json"
    with open(final_file, "w", encoding="utf-8") as f:
        json.dump(unique_events, f, ensure_ascii=False, indent=2)

    # Save stats
    stats["total_after_dedup"] = len(unique_events)
    stats_file = OUTPUT_DIR / "ultra_extraction_stats.json"
    with open(stats_file, "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)

    print(f"\n{'='*70}")
    print("ULTRA AGGRESSIVE EXTRACTION COMPLETE")
    print(f"{'='*70}")
    print(f"PDFs processed: {stats['pdfs_processed']}")
    print(f"Pass 1 (main): {stats['pass1_events']} events")
    print(f"Pass 2 (micro): {stats['pass2_events']} events")
    print(f"Knowledge cards: {stats['knowledge_events']} events")
    print(f"Total (raw): {stats['total_before_dedup']}")
    print(f"Final (dedup): {stats['total_after_dedup']}")
    print(f"\nAverage per PDF: {stats['total_after_dedup'] / max(stats['pdfs_processed'], 1):.1f}")

    print(f"\nBreakdown by PDF:")
    for pdf, count in sorted(stats['by_pdf'].items()):
        print(f"  {pdf:20s} {count:4d} events")

    return unique_events, stats


if __name__ == "__main__":
    print("CMSD - ULTRA AGGRESSIVE MULTI-PASS EXTRACTION")
    print("=" * 70)
    print("Strategy:")
    print("  1. PASS 1: Main events (40-80 per PDF)")
    print("  2. PASS 2: Micro details (20-50 per PDF)")
    print("  3. BONUS: Knowledge cards integration")
    print("Target: 500-700+ events!")
    print()

    events, stats = ultra_aggressive_extraction()

    print(f"\n[SUCCESS] {len(events)} events extracted!")
    print("Check data/processed/ultra_extraction_final.json")
