#!/usr/bin/env python3
"""
Database operations for CMSD Historical Timeline
Populates SQLite database from extracted JSON events
"""

import sqlite3
import json
from pathlib import Path
from typing import List, Dict, Any
import pandas as pd


PROJECT_ROOT = Path(__file__).parent.parent
DB_PATH = PROJECT_ROOT / "data" / "database" / "cmsd.db"
SCHEMA_PATH = PROJECT_ROOT / "data" / "database" / "schema.sql"
EVENTS_JSON = PROJECT_ROOT / "data" / "processed" / "final_complete_with_gemini.json"
CSV_OUTPUT = PROJECT_ROOT / "data" / "processed"


def create_database():
    """Create database and schema"""
    print("Creating database...")

    # Ensure directory exists
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    # Read schema
    with open(SCHEMA_PATH, 'r', encoding='utf-8') as f:
        schema_sql = f.read()

    # Create database
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Execute schema
    cursor.executescript(schema_sql)
    conn.commit()

    print(f"[OK] Database created: {DB_PATH}")
    return conn


def insert_event(cursor: sqlite3.Cursor, event: Dict[str, Any]) -> int:
    """Insert single event and return its ID"""

    # Convert lists to JSON strings
    tags_json = json.dumps(event.get('tags', []), ensure_ascii=False)
    bible_refs_json = json.dumps(event.get('bible_refs', []), ensure_ascii=False)

    cursor.execute("""
        INSERT INTO events (
            year, year_end, title, description, category,
            region, importance, tags, source_page, bible_refs
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        event.get('year'),
        event.get('year_end'),
        event['title'],
        event.get('description'),
        event.get('category'),
        event.get('region'),
        event.get('importance', 3),
        tags_json,
        event.get('source_page'),
        bible_refs_json
    ))

    return cursor.lastrowid


def get_or_create_person(cursor: sqlite3.Cursor, name: str) -> int:
    """Get person ID or create if doesn't exist"""
    cursor.execute("SELECT id FROM people WHERE name = ?", (name,))
    row = cursor.fetchone()

    if row:
        return row[0]

    cursor.execute("INSERT INTO people (name) VALUES (?)", (name,))
    return cursor.lastrowid


def get_or_create_place(cursor: sqlite3.Cursor, name: str) -> int:
    """Get place ID or create if doesn't exist"""
    cursor.execute("SELECT id FROM places WHERE name = ?", (name,))
    row = cursor.fetchone()

    if row:
        return row[0]

    cursor.execute("INSERT INTO places (name) VALUES (?)", (name,))
    return cursor.lastrowid


def populate_database(events: List[Dict[str, Any]]):
    """Populate database with extracted events"""
    conn = create_database()
    cursor = conn.cursor()

    print(f"\nPopulating database with {len(events)} events...")

    stats = {
        'events': 0,
        'people': 0,
        'places': 0,
        'relations': 0
    }

    for i, event in enumerate(events, 1):
        try:
            # Insert event
            event_id = insert_event(cursor, event)
            stats['events'] += 1

            # Link people
            for person_name in event.get('people', []):
                if person_name and person_name.strip():
                    person_id = get_or_create_person(cursor, person_name.strip())

                    # Link event-person
                    cursor.execute("""
                        INSERT OR IGNORE INTO event_people (event_id, person_id)
                        VALUES (?, ?)
                    """, (event_id, person_id))
                    stats['relations'] += 1

            # Link places
            for place_name in event.get('places', []):
                if place_name and place_name.strip():
                    place_id = get_or_create_place(cursor, place_name.strip())

                    # Link event-place
                    cursor.execute("""
                        INSERT OR IGNORE INTO event_places (event_id, place_id)
                        VALUES (?, ?)
                    """, (event_id, place_id))
                    stats['relations'] += 1

            if i % 50 == 0:
                print(f"  Processed {i}/{len(events)} events...")
                conn.commit()

        except Exception as e:
            print(f"  [ERROR] Inserting event '{event.get('title', 'unknown')}': {e}")

    # Final commit
    conn.commit()

    # Count unique people and places
    cursor.execute("SELECT COUNT(*) FROM people")
    stats['people'] = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM places")
    stats['places'] = cursor.fetchone()[0]

    conn.close()

    print(f"\n{'='*60}")
    print(f"DATABASE POPULATION COMPLETE")
    print(f"{'='*60}")
    print(f"Events: {stats['events']}")
    print(f"People: {stats['people']}")
    print(f"Places: {stats['places']}")
    print(f"Relations: {stats['relations']}")

    return stats


def export_to_csv():
    """Export database tables to CSV files"""
    print("\nExporting to CSV...")

    conn = sqlite3.connect(DB_PATH)

    # Export events
    events_df = pd.read_sql_query("SELECT * FROM events ORDER BY year", conn)
    events_csv = CSV_OUTPUT / "events.csv"
    events_df.to_csv(events_csv, index=False, encoding='utf-8')
    print(f"[OK] Exported {len(events_df)} events to {events_csv.name}")

    # Export people
    people_df = pd.read_sql_query("SELECT * FROM people ORDER BY name", conn)
    people_csv = CSV_OUTPUT / "people.csv"
    people_df.to_csv(people_csv, index=False, encoding='utf-8')
    print(f"[OK] Exported {len(people_df)} people to {people_csv.name}")

    # Export places
    places_df = pd.read_sql_query("SELECT * FROM places ORDER BY name", conn)
    places_csv = CSV_OUTPUT / "places.csv"
    places_df.to_csv(places_csv, index=False, encoding='utf-8')
    print(f"[OK] Exported {len(places_df)} places to {places_csv.name}")

    # Export timeline view
    timeline_df = pd.read_sql_query("SELECT * FROM timeline", conn)
    timeline_csv = CSV_OUTPUT / "timeline.csv"
    timeline_df.to_csv(timeline_csv, index=False, encoding='utf-8')
    print(f"[OK] Exported {len(timeline_df)} timeline entries to {timeline_csv.name}")

    # Export full JSON
    timeline_json = CSV_OUTPUT / "timeline.json"
    timeline_df.to_json(timeline_json, orient='records', force_ascii=False, indent=2)
    print(f"[OK] Exported timeline to {timeline_json.name}")

    conn.close()


if __name__ == "__main__":
    # Load extracted events
    if not EVENTS_JSON.exists():
        print(f"Error: {EVENTS_JSON} not found. Run extract.py first!")
        exit(1)

    with open(EVENTS_JSON, 'r', encoding='utf-8') as f:
        events = json.load(f)

    # Populate database
    stats = populate_database(events)

    # Export to CSV
    export_to_csv()

    print("\n[OK] Done!")
