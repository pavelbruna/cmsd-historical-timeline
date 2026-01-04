#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CMSD - Remove Duplicates from Database
"""
import sqlite3
import json
import sys
from pathlib import Path
from typing import List, Dict, Set, Tuple
import pandas as pd

# Fix Windows encoding for emoji
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

PROJECT_ROOT = Path(__file__).parent.parent
DB_PATH = PROJECT_ROOT / "data" / "database" / "cmsd.db"
BACKUP_PATH = PROJECT_ROOT / "data" / "database" / "cmsd_backup.db"
CSV_OUTPUT = PROJECT_ROOT / "data" / "processed"

def analyze_duplicates(db_path: Path) -> Dict:
    """Analyze duplicate patterns"""
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    print("🔍 Analyzing duplicates...")
    print("=" * 60)

    # 1. EXACT duplicates (title + year + source_page)
    cursor.execute("""
        SELECT title, year, source_page, COUNT(*) as count
        FROM events
        GROUP BY title, year, source_page
        HAVING count > 1
        ORDER BY count DESC
    """)
    exact_dupes = cursor.fetchall()

    # 2. SIMILAR events (title + year, different sources)
    cursor.execute("""
        SELECT title, year, COUNT(*) as count,
               GROUP_CONCAT(source_page) as sources,
               GROUP_CONCAT(id) as ids
        FROM events
        GROUP BY title, year
        HAVING count > 1
        ORDER BY count DESC
    """)
    similar_dupes = cursor.fetchall()

    # 3. YEAR-only duplicates (same year, very similar title)
    cursor.execute("""
        SELECT year, COUNT(*) as count
        FROM events
        GROUP BY year
        HAVING count > 5
        ORDER BY count DESC
        LIMIT 20
    """)
    year_clusters = cursor.fetchall()

    conn.close()

    stats = {
        'exact_duplicates': len(exact_dupes),
        'similar_events': len(similar_dupes),
        'total_events': get_total_count(db_path)
    }

    print(f"📊 Results:")
    print(f"  Total events: {stats['total_events']}")
    print(f"  Exact duplicates: {stats['exact_duplicates']} groups")
    print(f"  Similar events: {stats['similar_events']} groups")
    print()

    if exact_dupes:
        print("⚠️ Top 10 exact duplicates:")
        for title, year, source, count in exact_dupes[:10]:
            print(f"  • {title} ({year}, {source}): {count}× duplicated")
        print()

    if similar_dupes:
        print("⚠️ Top 10 similar events:")
        for title, year, count, sources, ids in similar_dupes[:10]:
            print(f"  • {title} ({year}): {count}× in sources: {sources}")
        print()

    return {
        'exact': exact_dupes,
        'similar': similar_dupes,
        'stats': stats
    }

def get_total_count(db_path: Path) -> int:
    """Get total event count"""
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM events")
    count = cursor.fetchone()[0]
    conn.close()
    return count

def remove_exact_duplicates(db_path: Path, dry_run: bool = True) -> int:
    """Remove exact duplicates (keep first occurrence)"""
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    # Find duplicates
    cursor.execute("""
        WITH duplicates AS (
            SELECT id, title, year, source_page,
                   ROW_NUMBER() OVER (
                       PARTITION BY title, year, source_page
                       ORDER BY id
                   ) as rn
            FROM events
        )
        SELECT id FROM duplicates WHERE rn > 1
    """)

    duplicate_ids = [row[0] for row in cursor.fetchall()]

    if not duplicate_ids:
        print("✅ No exact duplicates found!")
        conn.close()
        return 0

    print(f"Found {len(duplicate_ids)} exact duplicate events")

    if dry_run:
        print("🔍 DRY RUN - no changes made")
        print(f"Would delete IDs: {duplicate_ids[:20]}...")
    else:
        # Delete duplicates
        placeholders = ','.join('?' * len(duplicate_ids))
        cursor.execute(f"DELETE FROM events WHERE id IN ({placeholders})", duplicate_ids)
        conn.commit()
        print(f"✅ Deleted {len(duplicate_ids)} exact duplicates")

    conn.close()
    return len(duplicate_ids)

def merge_similar_events(db_path: Path, dry_run: bool = True) -> int:
    """Merge similar events (same title + year, different sources)"""
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    # Find similar events
    cursor.execute("""
        SELECT title, year, GROUP_CONCAT(id) as ids,
               GROUP_CONCAT(source_page) as sources
        FROM events
        GROUP BY title, year
        HAVING COUNT(*) > 1
    """)

    similar_groups = cursor.fetchall()
    merged_count = 0

    for title, year, ids_str, sources_str in similar_groups:
        ids = [int(x) for x in ids_str.split(',')]
        sources = sources_str.split(',')

        if len(ids) < 2:
            continue

        # Keep first, merge sources, delete rest
        keep_id = ids[0]
        delete_ids = ids[1:]
        merged_sources = ','.join(sorted(set(sources)))

        print(f"Merging: {title} ({year}) - {len(ids)} duplicates")
        print(f"  Sources: {merged_sources}")
        print(f"  Keep ID: {keep_id}, Delete: {delete_ids}")

        if not dry_run:
            # Update kept event with merged sources
            cursor.execute("""
                UPDATE events
                SET source_page = ?
                WHERE id = ?
            """, (merged_sources, keep_id))

            # Delete duplicates
            placeholders = ','.join('?' * len(delete_ids))
            cursor.execute(f"DELETE FROM events WHERE id IN ({placeholders})", delete_ids)

            merged_count += len(delete_ids)

    if not dry_run:
        conn.commit()
        print(f"✅ Merged {merged_count} duplicate events")
    else:
        print(f"🔍 DRY RUN - would merge {len(similar_groups)} groups")

    conn.close()
    return merged_count

def backup_database(db_path: Path, backup_path: Path):
    """Create backup before deduplication"""
    import shutil
    shutil.copy2(db_path, backup_path)
    print(f"✅ Backup created: {backup_path}")

def export_to_csv(db_path: Path):
    """Export database tables to CSV files"""
    conn = sqlite3.connect(str(db_path))

    # Export events
    events_df = pd.read_sql_query("SELECT * FROM events ORDER BY year", conn)
    events_csv = CSV_OUTPUT / "events.csv"
    events_df.to_csv(events_csv, index=False, encoding='utf-8')
    print(f"  ✅ Exported {len(events_df)} events to {events_csv.name}")

    # Export people
    people_df = pd.read_sql_query("SELECT * FROM people ORDER BY name", conn)
    people_csv = CSV_OUTPUT / "people.csv"
    people_df.to_csv(people_csv, index=False, encoding='utf-8')
    print(f"  ✅ Exported {len(people_df)} people to {people_csv.name}")

    # Export places
    places_df = pd.read_sql_query("SELECT * FROM places ORDER BY name", conn)
    places_csv = CSV_OUTPUT / "places.csv"
    places_df.to_csv(places_csv, index=False, encoding='utf-8')
    print(f"  ✅ Exported {len(places_df)} places to {places_csv.name}")

    # Export timeline view
    timeline_df = pd.read_sql_query("SELECT * FROM timeline", conn)
    timeline_csv = CSV_OUTPUT / "timeline.csv"
    timeline_df.to_csv(timeline_csv, index=False, encoding='utf-8')
    print(f"  ✅ Exported {len(timeline_df)} timeline entries to {timeline_csv.name}")

    # Export full JSON
    timeline_json = CSV_OUTPUT / "timeline.json"
    timeline_df.to_json(timeline_json, orient='records', force_ascii=False, indent=2)
    print(f"  ✅ Exported timeline to {timeline_json.name}")

    conn.close()

def main():
    print("=" * 60)
    print("CMSD DATABASE DEDUPLICATION")
    print("=" * 60)
    print()

    # 1. Backup
    print("📦 Step 1: Creating backup...")
    backup_database(DB_PATH, BACKUP_PATH)
    print()

    # 2. Analyze
    print("📊 Step 2: Analyzing duplicates...")
    analysis = analyze_duplicates(DB_PATH)
    print()

    # 3. Dry run
    print("🔍 Step 3: Dry run (preview changes)...")
    print()
    print("--- Removing exact duplicates ---")
    exact_removed = remove_exact_duplicates(DB_PATH, dry_run=True)
    print()
    print("--- Merging similar events ---")
    similar_merged = merge_similar_events(DB_PATH, dry_run=True)
    print()

    # 4. Confirm
    total_changes = exact_removed + similar_merged
    print("=" * 60)
    print(f"📊 Summary:")
    print(f"  Current events: {analysis['stats']['total_events']}")
    print(f"  To remove: {total_changes}")
    print(f"  After cleanup: {analysis['stats']['total_events'] - total_changes}")
    print("=" * 60)
    print()

    response = input("🤔 Proceed with deduplication? (yes/no): ")

    if response.lower() in ['yes', 'y']:
        print()
        print("🧹 Performing deduplication...")
        print()

        # Remove exact duplicates
        exact_count = remove_exact_duplicates(DB_PATH, dry_run=False)

        # Merge similar events
        similar_count = merge_similar_events(DB_PATH, dry_run=False)

        # Final stats
        final_count = get_total_count(DB_PATH)

        print()
        print("=" * 60)
        print("✅ DEDUPLICATION COMPLETE!")
        print("=" * 60)
        print(f"  Before: {analysis['stats']['total_events']} events")
        print(f"  Removed: {exact_count + similar_count} duplicates")
        print(f"  After: {final_count} events")
        print(f"  Backup: {BACKUP_PATH}")
        print("=" * 60)

        # Export CSVs (without regenerating database!)
        print()
        print("📄 Exporting to CSV...")
        export_to_csv(DB_PATH)

    else:
        print("❌ Cancelled - no changes made")
        print(f"💡 Backup exists at: {BACKUP_PATH}")

if __name__ == "__main__":
    main()
