# Database Schema Documentation

## Overview

CMSD Historical Timeline používá SQLite databázi s následujícími tabulkami:

```
events ───┬─── event_people ─── people
          │
          └─── event_places ─── places
```

---

## Tables

### `events`

Hlavní tabulka historických událostí.

| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER | Primary key |
| `year` | INTEGER | Rok události (záporné = př.n.l., kladné = n.l.) |
| `year_end` | INTEGER | Konec období (NULL pro jednotlivou událost) |
| `title` | TEXT | Název události (max 100 znaků) |
| `description` | TEXT | Detailní popis |
| `category` | TEXT | Kategorie: religion/war/politics/discovery/culture/science |
| `region` | TEXT | Geografická oblast |
| `importance` | INTEGER | Důležitost 1-5 (5 = nejvyšší) |
| `tags` | TEXT | JSON array tagů |
| `source_page` | TEXT | Zdroj (např. "2L") |
| `bible_refs` | TEXT | JSON array biblických odkazů |
| `created_at` | TIMESTAMP | Časové razítko |

**Indexes:**
- `idx_events_year` - Optimalizace pro vyhledávání podle roku
- `idx_events_category` - Filtrování podle kategorie
- `idx_events_region` - Geografické filtrování
- `idx_events_importance` - Řazení podle důležitosti

**Full-text search:**
- `events_fts` - FTS5 tabulka pro fulltext vyhledávání v `title` a `description`

---

### `people`

Historické postavy.

| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER | Primary key |
| `name` | TEXT | Jméno (UNIQUE) |
| `birth_year` | INTEGER | Rok narození |
| `death_year` | INTEGER | Rok smrti |
| `description` | TEXT | Popis osoby |
| `role` | TEXT | Role (emperor/prophet/explorer/etc) |
| `created_at` | TIMESTAMP | Časové razítko |

**Indexes:**
- `idx_people_name` - Vyhledávání podle jména
- `idx_people_birth_year` - Řazení podle data narození

---

### `places`

Geografické lokace.

| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER | Primary key |
| `name` | TEXT | Název místa (UNIQUE) |
| `type` | TEXT | Typ (city/country/empire/region/mountain) |
| `latitude` | REAL | Zeměpisná šířka |
| `longitude` | REAL | Zeměpisná délka |
| `description` | TEXT | Popis místa |
| `created_at` | TIMESTAMP | Časové razítko |

**Indexes:**
- `idx_places_name` - Vyhledávání podle názvu
- `idx_places_type` - Filtrování podle typu

---

### `event_people`

Many-to-many vztah mezi událostmi a osobami.

| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER | Primary key |
| `event_id` | INTEGER | FK → events(id) |
| `person_id` | INTEGER | FK → people(id) |
| `role` | TEXT | Role v události |

**Indexes:**
- `idx_event_people_event`
- `idx_event_people_person`

---

### `event_places`

Many-to-many vztah mezi událostmi a místy.

| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER | Primary key |
| `event_id` | INTEGER | FK → events(id) |
| `place_id` | INTEGER | FK → places(id) |

**Indexes:**
- `idx_event_places_event`
- `idx_event_places_place`

---

## Views

### `events_with_details`

Denormalizovaný view s agregovanými daty.

```sql
SELECT * FROM events_with_details WHERE year = 1492;
```

| Column | Description |
|--------|-------------|
| Všechny sloupce z `events` | ... |
| `people_names` | Comma-separated seznam osob |
| `place_names` | Comma-separated seznam míst |

---

### `timeline`

Chronologicky seřazená časová osa.

```sql
SELECT * FROM timeline ORDER BY year;
```

Přidává sloupec `year_display` s formátovaným rokem (např. "608 př.n.l.").

---

## Example Queries

### Vyhledávání podle roku

```sql
-- Události v roce 1492
SELECT * FROM events WHERE year = 1492;

-- Události v období
SELECT * FROM events WHERE year BETWEEN -1000 AND -500;

-- Biblická chronologie (BC)
SELECT * FROM events WHERE year < 0 ORDER BY year;
```

### Fulltextové vyhledávání

```sql
-- Vyhledat "potopa"
SELECT e.*
FROM events e
JOIN events_fts fts ON e.id = fts.rowid
WHERE events_fts MATCH 'potopa'
ORDER BY rank;
```

### Propojení s osobami

```sql
-- Události s Alexandrem Velikým
SELECT e.year, e.title, p.name
FROM events e
JOIN event_people ep ON e.id = ep.event_id
JOIN people p ON ep.person_id = p.id
WHERE p.name LIKE '%Alexander%';

-- Všechny osoby v události
SELECT
    e.title,
    GROUP_CONCAT(p.name, ', ') as people
FROM events e
LEFT JOIN event_people ep ON e.id = ep.event_id
LEFT JOIN people p ON ep.person_id = p.id
GROUP BY e.id;
```

### Geografické vyhledávání

```sql
-- Události v Evropě
SELECT * FROM events
WHERE region LIKE '%Evropa%'
ORDER BY year;

-- Události spojené s místem
SELECT e.year, e.title, pl.name as place
FROM events e
JOIN event_places epl ON e.id = epl.event_id
JOIN places pl ON epl.place_id = pl.id
WHERE pl.name = 'Řím';
```

### Statistiky

```sql
-- Počet událostí podle kategorie
SELECT category, COUNT(*) as count
FROM events
GROUP BY category
ORDER BY count DESC;

-- Nejdůležitější události
SELECT year, title, importance
FROM events
WHERE importance >= 4
ORDER BY year;

-- Timeline coverage
SELECT
    MIN(year) as earliest_event,
    MAX(year) as latest_event,
    COUNT(*) as total_events
FROM events;
```

### Biblické odkazy

```sql
-- Události s biblickými odkazy
SELECT year, title, bible_refs
FROM events
WHERE bible_refs != '[]' AND bible_refs IS NOT NULL
ORDER BY year;
```

---

## Data Integrity

### Constraints

- `events.importance` - CHECK (1-5)
- `people.name` - UNIQUE
- `places.name` - UNIQUE
- `event_people` - UNIQUE(event_id, person_id)
- `event_places` - UNIQUE(event_id, place_id)

### Foreign Keys

- Cascade deletes enabled
- Referential integrity enforced

### Triggers

- `events_fts_insert` - Auto-update FTS on insert
- `events_fts_update` - Auto-update FTS on update
- `events_fts_delete` - Auto-update FTS on delete

---

## Maintenance

### Vacuum database

```sql
VACUUM;
```

### Rebuild FTS index

```sql
INSERT INTO events_fts(events_fts) VALUES('rebuild');
```

### Check integrity

```sql
PRAGMA integrity_check;
PRAGMA foreign_key_check;
```

---

## Performance Tips

1. **Indexy jsou klíčové** - Vždy používej WHERE na indexované sloupce
2. **FTS pro text** - Pro vyhledávání v textu používej `events_fts` view
3. **LIMIT queries** - Pro velké resultsety používej LIMIT + OFFSET
4. **JSON parsing** - Tags a bible_refs jsou JSON - parse v aplikaci

---

## Export/Import

### Export to JSON

```bash
sqlite3 cmsd.db "SELECT json_group_array(json_object(
    'year', year,
    'title', title,
    'description', description
)) FROM events" > events.json
```

### Backup

```bash
sqlite3 cmsd.db ".backup cmsd_backup.db"
```

---

Last updated: January 2026
