#!/usr/bin/env python3
"""Merge all extracted PDFs into final dataset"""

import json
from pathlib import Path
from typing import List, Dict, Any

PROJECT_ROOT = Path(".")
GEMINI_DIR = PROJECT_ROOT / "data" / "processed" / "gemini_ultra"
OUTPUT_DIR = PROJECT_ROOT / "data" / "processed"

def deduplicate_events(events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Deduplicate based on (title, year, source_page)"""
    seen = set()
    unique = []

    for event in events:
        if event.get('year') is None:
            continue

        key = (
            event.get('title', '').lower().strip(),
            event.get('year'),
            event.get('source_page', '')
        )

        if key not in seen:
            seen.add(key)
            unique.append(event)

    return unique

def merge_all():
    """Merge all Gemini extractions"""
    print("="*70)
    print("FINAL MERGE - ALL 19 PDFs")
    print("="*70)

    all_events = []
    by_pdf = {}

    # Load all Gemini extractions
    gemini_files = sorted(GEMINI_DIR.glob("*_gemini.json"))

    print(f"\nFound {len(gemini_files)} Gemini extractions:")

    for file in gemini_files:
        try:
            with open(file, 'r', encoding='utf-8') as f:
                events = json.load(f)

            pdf_name = file.stem.replace('_gemini', '')
            by_pdf[pdf_name] = len(events)

            if len(events) > 0:
                all_events.extend(events)
                print(f"  [OK] {pdf_name:20s} {len(events):4d} events")
            else:
                print(f"  [EMPTY] {pdf_name}")

        except Exception as e:
            print(f"  [ERROR] {file.name}: {e}")

    print(f"\n[TOTAL] Before dedup: {len(all_events)} events")

    # Deduplicate
    unique_events = deduplicate_events(all_events)
    print(f"[DEDUP] After dedup: {len(unique_events)} unique events")
    print(f"[REMOVED] {len(all_events) - len(unique_events)} duplicates")

    # Sort by year
    unique_events.sort(key=lambda e: e.get('year', 0))

    # Save final
    final_file = OUTPUT_DIR / "final_complete_all_19_pdfs.json"
    with open(final_file, 'w', encoding='utf-8') as f:
        json.dump(unique_events, f, ensure_ascii=False, indent=2)

    print(f"\n[SAVED] {final_file.name}")

    # Stats
    categories = {}
    for event in unique_events:
        cat = event.get('category', 'unknown')
        categories[cat] = categories.get(cat, 0) + 1

    regions = {}
    for event in unique_events:
        reg = event.get('region', 'unknown')
        if reg and reg != 'unknown':
            regions[reg] = regions.get(reg, 0) + 1

    stats = {
        "total_events": len(unique_events),
        "total_pdfs": len(by_pdf),
        "by_pdf": dict(sorted(by_pdf.items())),
        "by_category": dict(sorted(categories.items(), key=lambda x: -x[1])),
        "by_region": dict(sorted(regions.items(), key=lambda x: -x[1])[:20]),
        "duplicates_removed": len(all_events) - len(unique_events),
        "improvement": f"70 -> {len(unique_events)} events ({len(unique_events)/70:.1f}× improvement)"
    }

    stats_file = OUTPUT_DIR / "final_complete_stats.json"
    with open(stats_file, 'w', encoding='utf-8') as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)

    print(f"[SAVED] {stats_file.name}")

    print(f"\n{'='*70}")
    print("FINAL MERGE COMPLETE!")
    print("="*70)
    print(f"Total unique events: {len(unique_events)}")
    print(f"Journey: 70 -> {len(unique_events)} events ({len(unique_events)/70:.1f}× improvement)")

    print(f"\nTop categories:")
    for cat, count in sorted(categories.items(), key=lambda x: -x[1])[:8]:
        print(f"  {cat:20s} {count:4d}")

    print(f"\nTop regions:")
    for reg, count in list(sorted(regions.items(), key=lambda x: -x[1]))[:8]:
        print(f"  {reg:20s} {count:4d}")

    return unique_events, stats

if __name__ == "__main__":
    print("CMSD Historical Timeline - Final Merge")
    print()

    events, stats = merge_all()

    print(f"\n[SUCCESS] {len(events)} unique events ready for database!")
    print("\nNext: Update database with:")
    print("  python scripts/database.py")
