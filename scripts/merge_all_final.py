#!/usr/bin/env python3
"""
Final merge: Combine existing 1704 events + remaining 7 PDFs
"""

import json
from pathlib import Path
from typing import List, Dict, Any

PROJECT_ROOT = Path(__file__).parent.parent
GEMINI_ULTRA_DIR = PROJECT_ROOT / "data" / "processed" / "gemini_ultra"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"


def deduplicate_events(events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Deduplicate events based on (title, year, source_page)"""
    seen = set()
    unique = []

    for event in events:
        # Skip events without year
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


def merge_all_final():
    """Final merge of all extraction data"""
    print("="*70)
    print("FINAL MERGE - ALL PDFs")
    print("="*70)

    # Load existing 1704 events
    existing_file = PROCESSED_DIR / "final_with_gemini_ultra.json"
    with open(existing_file, 'r', encoding='utf-8') as f:
        existing_events = json.load(f)
    print(f"[LOAD] Existing data: {len(existing_events)} events")

    # Load remaining 7 PDFs
    remaining_file = GEMINI_ULTRA_DIR / "remaining_7_gemini.json"
    if remaining_file.exists():
        with open(remaining_file, 'r', encoding='utf-8') as f:
            remaining_events = json.load(f)
        print(f"[LOAD] Remaining 7 PDFs: {len(remaining_events)} events")
    else:
        print("[ERROR] remaining_7_gemini.json not found!")
        print("Run extract_remaining_pdfs.py first!")
        return

    # Combine
    all_events = existing_events + remaining_events
    print(f"\n[TOTAL] Before dedup: {len(all_events)} events")
    print(f"  Existing (12 PDFs): {len(existing_events)}")
    print(f"  Remaining (7 PDFs): {len(remaining_events)}")

    # Deduplicate
    unique_events = deduplicate_events(all_events)
    print(f"\n[DEDUP] After dedup: {len(unique_events)} unique events")
    print(f"[REMOVED] {len(all_events) - len(unique_events)} duplicates")

    # Sort by year
    unique_events.sort(key=lambda e: e.get('year', 0))

    # Save final
    final_file = PROCESSED_DIR / "final_complete_all_pdfs.json"
    with open(final_file, 'w', encoding='utf-8') as f:
        json.dump(unique_events, f, ensure_ascii=False, indent=2)

    print(f"\n[SAVED] {final_file.name}")

    # Stats
    stats = {
        "total_events": len(unique_events),
        "sources": {
            "first_12_pdfs": len(existing_events),
            "final_7_pdfs": len(remaining_events)
        },
        "duplicates_removed": len(all_events) - len(unique_events),
        "improvement": f"70 -> {len(unique_events)} ({len(unique_events)/70:.1f}× improvement)"
    }

    # Category breakdown
    categories = {}
    for event in unique_events:
        cat = event.get('category', 'unknown')
        categories[cat] = categories.get(cat, 0) + 1

    stats['by_category'] = categories

    # PDFs breakdown
    by_pdf = {}
    for event in unique_events:
        pdf = event.get('source_page', 'unknown')
        by_pdf[pdf] = by_pdf.get(pdf, 0) + 1

    stats['by_pdf'] = dict(sorted(by_pdf.items(), key=lambda x: -x[1]))

    # Save stats
    stats_file = PROCESSED_DIR / "final_complete_stats.json"
    with open(stats_file, 'w', encoding='utf-8') as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)

    print(f"[SAVED] {stats_file.name}")

    print(f"\n{'='*70}")
    print("FINAL MERGE COMPLETE!")
    print("="*70)
    print(f"Total unique events: {len(unique_events)}")
    print(f"Journey: 70 -> {len(unique_events)} events ({len(unique_events)/70:.1f}× improvement)")
    print(f"\nCategory breakdown:")
    for cat, count in sorted(categories.items(), key=lambda x: -x[1])[:10]:
        print(f"  {cat:20s} {count:4d}")

    print(f"\nTop 10 PDFs:")
    for pdf, count in list(stats['by_pdf'].items())[:10]:
        print(f"  {pdf:20s} {count:4d} events")

    return unique_events, stats


if __name__ == "__main__":
    print("CMSD - Final Merge of All PDFs")
    print()

    events, stats = merge_all_final()

    print(f"\n[SUCCESS] {len(events)} unique events ready for database!")
    print("\nNext step: Update database with:")
    print("  python scripts/database.py")
