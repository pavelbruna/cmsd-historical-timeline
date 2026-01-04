#!/usr/bin/env python3
"""
Merge all Gemini ultra extraction files into one combined file
"""

import json
from pathlib import Path
from typing import List, Dict, Any

PROJECT_ROOT = Path(__file__).parent.parent
GEMINI_ULTRA_DIR = PROJECT_ROOT / "data" / "processed" / "gemini_ultra"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"


def merge_gemini_ultra():
    """Merge all individual Gemini ultra files"""
    print("="*70)
    print("MERGING GEMINI ULTRA FILES")
    print("="*70)

    all_events = []
    stats = {"total_events": 0, "by_file": {}, "errors": []}

    # Load all *_gemini.json files
    gemini_files = sorted(GEMINI_ULTRA_DIR.glob("*_gemini.json"))

    for file in gemini_files:
        try:
            # Skip empty files
            if file.stat().st_size <= 10:
                print(f"[SKIP] {file.name} (empty)")
                stats["by_file"][file.name] = 0
                continue

            with open(file, 'r', encoding='utf-8') as f:
                events = json.load(f)

            print(f"[LOAD] {file.name}: {len(events)} events")
            all_events.extend(events)
            stats["by_file"][file.name] = len(events)
            stats["total_events"] += len(events)

        except Exception as e:
            print(f"[ERROR] {file.name}: {e}")
            stats["errors"].append(file.name)
            stats["by_file"][file.name] = 0

    # Save combined file
    combined_file = GEMINI_ULTRA_DIR / "all_pdfs_gemini_ultra.json"
    with open(combined_file, 'w', encoding='utf-8') as f:
        json.dump(all_events, f, ensure_ascii=False, indent=2)

    print(f"\n[SAVED] {combined_file.name}")
    print(f"Total events: {stats['total_events']}")

    # Save stats
    stats_file = GEMINI_ULTRA_DIR / "gemini_ultra_merge_stats.json"
    with open(stats_file, 'w', encoding='utf-8') as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)

    print(f"[SAVED] {stats_file.name}")

    # Now merge with existing data
    print(f"\n{'='*70}")
    print("MERGING WITH EXISTING DATA")
    print("="*70)

    # Load existing data
    existing_file = PROCESSED_DIR / "final_complete_with_gemini.json"
    if existing_file.exists():
        with open(existing_file, 'r', encoding='utf-8') as f:
            existing_events = json.load(f)
        print(f"[LOAD] Existing data: {len(existing_events)} events")
    else:
        existing_events = []
        print("[INFO] No existing data found")

    # Combine
    combined_events = existing_events + all_events
    print(f"\n[TOTAL] Before dedup: {len(combined_events)} events")
    print(f"  Existing: {len(existing_events)}")
    print(f"  Gemini ultra: {len(all_events)}")

    # Deduplicate
    unique_events = deduplicate_events(combined_events)
    print(f"\n[DEDUP] After dedup: {len(unique_events)} unique events")
    print(f"[REMOVED] {len(combined_events) - len(unique_events)} duplicates")

    # Sort by year
    unique_events.sort(key=lambda e: e.get('year', 0))

    # Save final
    final_file = PROCESSED_DIR / "final_with_gemini_ultra.json"
    with open(final_file, 'w', encoding='utf-8') as f:
        json.dump(unique_events, f, ensure_ascii=False, indent=2)

    print(f"\n[SAVED] {final_file.name}")

    # Stats
    final_stats = {
        "total_events": len(unique_events),
        "sources": {
            "existing": len(existing_events),
            "gemini_ultra": len(all_events)
        },
        "duplicates_removed": len(combined_events) - len(unique_events),
        "improvement": f"{len(existing_events)} -> {len(unique_events)} (+{len(unique_events) - len(existing_events)})"
    }

    # Category breakdown
    categories = {}
    for event in unique_events:
        cat = event.get('category', 'unknown')
        categories[cat] = categories.get(cat, 0) + 1

    final_stats['by_category'] = categories

    # Save final stats
    final_stats_file = PROCESSED_DIR / "final_gemini_ultra_stats.json"
    with open(final_stats_file, 'w', encoding='utf-8') as f:
        json.dump(final_stats, f, ensure_ascii=False, indent=2)

    print(f"[SAVED] {final_stats_file.name}")

    print(f"\n{'='*70}")
    print("MERGE COMPLETE!")
    print("="*70)
    print(f"Total unique events: {len(unique_events)}")
    print(f"Improvement: {len(existing_events)} -> {len(unique_events)} (+{len(unique_events) - len(existing_events)})")
    print(f"\nCategory breakdown:")
    for cat, count in sorted(categories.items(), key=lambda x: -x[1])[:10]:
        print(f"  {cat:15s} {count:4d}")

    if stats["errors"]:
        print(f"\nErrors: {len(stats['errors'])}")
        for err in stats["errors"]:
            print(f"  - {err}")

    return unique_events, final_stats


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


if __name__ == "__main__":
    events, stats = merge_gemini_ultra()
    print(f"\n[SUCCESS] {len(events)} unique events ready for database!")
