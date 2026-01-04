#!/usr/bin/env python3
"""
CMSD - Merge Left Pages with Existing Data
Combine all Left pages + existing 370 events + deduplicate
"""

import json
from pathlib import Path
from typing import List, Dict, Any

PROJECT_ROOT = Path(__file__).parent.parent
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"


def load_json(file_path: Path) -> List[Dict[str, Any]]:
    """Load JSON file"""
    if not file_path.exists():
        print(f"[SKIP] {file_path.name} not found")
        return []

    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    print(f"[LOAD] {file_path.name}: {len(data)} events")
    return data


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


def merge_all_with_left():
    """Merge all data including Left pages"""
    print("="*70)
    print("MERGING ALL DATA + LEFT PAGES")
    print("="*70)

    all_events = []

    # Load existing data
    existing = load_json(PROCESSED_DIR / "final_merged_events.json")
    all_events.extend(existing)

    # Load all Left pages
    left_pages = [
        "1L_single.json",
        "2L_left.json",
        "3L_left.json",
        "4L_left.json",
        "5L_left.json",
        "6L_left.json",
        "7L_single.json",
        "8L_single.json"
    ]

    left_count = 0
    for left_file in left_pages:
        left_path = PROCESSED_DIR / left_file
        left_events = load_json(left_path)
        all_events.extend(left_events)
        left_count += len(left_events)

    print(f"\n[TOTAL] Before dedup: {len(all_events)} events")
    print(f"  Existing: {len(existing)}")
    print(f"  Left pages: {left_count}")

    # Deduplicate
    unique_events = deduplicate_events(all_events)
    print(f"\n[DEDUP] After dedup: {len(unique_events)} unique events")
    print(f"[REMOVED] {len(all_events) - len(unique_events)} duplicates")

    # Sort by year
    unique_events.sort(key=lambda e: e.get('year', 0))

    # Save final merged
    final_file = PROCESSED_DIR / "final_with_left_pages.json"
    with open(final_file, 'w', encoding='utf-8') as f:
        json.dump(unique_events, f, ensure_ascii=False, indent=2)

    print(f"\n[SAVED] {final_file.name}")

    # Generate stats
    stats = {
        "total_events": len(unique_events),
        "sources": {
            "previous_merged": len(existing),
            "left_pages": left_count
        },
        "duplicates_removed": len(all_events) - len(unique_events)
    }

    # Category breakdown
    categories = {}
    for event in unique_events:
        cat = event.get('category', 'unknown')
        categories[cat] = categories.get(cat, 0) + 1

    stats['by_category'] = categories

    # Save stats
    stats_file = PROCESSED_DIR / "final_with_left_stats.json"
    with open(stats_file, 'w', encoding='utf-8') as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)

    print(f"[SAVED] {stats_file.name}")

    print("\n" + "="*70)
    print("MERGE WITH LEFT PAGES COMPLETE")
    print("="*70)
    print(f"Total unique events: {len(unique_events)}")
    print(f"Improvement: 370 -> {len(unique_events)} (+{len(unique_events) - 370})")
    print(f"\nCategory breakdown:")
    for cat, count in sorted(categories.items(), key=lambda x: -x[1]):
        print(f"  {cat:15s} {count:4d}")

    return unique_events, stats


if __name__ == "__main__":
    events, stats = merge_all_with_left()
    print(f"\n[SUCCESS] {len(events)} events ready for database!")
