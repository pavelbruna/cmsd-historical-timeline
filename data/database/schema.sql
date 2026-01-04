-- CMSD Historical Timeline Database Schema
-- SQLite version

-- Events table - core historical events
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    year INTEGER,                    -- Year (negative for BC, positive for AD)
    year_end INTEGER,                -- End year for periods (NULL for single events)
    title TEXT NOT NULL,             -- Event title
    description TEXT,                -- Detailed description
    category TEXT,                   -- religion/war/politics/discovery/culture/science
    region TEXT,                     -- Geographic region
    importance INTEGER DEFAULT 3,   -- Importance 1-5
    tags TEXT,                       -- JSON array of tags
    source_page TEXT,                -- Source PDF page (e.g., "2L")
    bible_refs TEXT,                 -- JSON array of Bible references
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CHECK (importance >= 1 AND importance <= 5)
);

-- People table - historical figures
CREATE TABLE IF NOT EXISTS people (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    birth_year INTEGER,
    death_year INTEGER,
    description TEXT,
    role TEXT,                       -- emperor/prophet/explorer/scientist/etc
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Places table - geographic locations
CREATE TABLE IF NOT EXISTS places (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    type TEXT,                       -- city/country/empire/region/mountain/etc
    latitude REAL,
    longitude REAL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Event-People relation (many-to-many)
CREATE TABLE IF NOT EXISTS event_people (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id INTEGER NOT NULL,
    person_id INTEGER NOT NULL,
    role TEXT,                       -- Role in the event

    FOREIGN KEY (event_id) REFERENCES events(id) ON DELETE CASCADE,
    FOREIGN KEY (person_id) REFERENCES people(id) ON DELETE CASCADE,
    UNIQUE(event_id, person_id)
);

-- Event-Places relation (many-to-many)
CREATE TABLE IF NOT EXISTS event_places (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id INTEGER NOT NULL,
    place_id INTEGER NOT NULL,

    FOREIGN KEY (event_id) REFERENCES events(id) ON DELETE CASCADE,
    FOREIGN KEY (place_id) REFERENCES places(id) ON DELETE CASCADE,
    UNIQUE(event_id, place_id)
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_events_year ON events(year);
CREATE INDEX IF NOT EXISTS idx_events_category ON events(category);
CREATE INDEX IF NOT EXISTS idx_events_region ON events(region);
CREATE INDEX IF NOT EXISTS idx_events_importance ON events(importance);
CREATE INDEX IF NOT EXISTS idx_events_source_page ON events(source_page);

CREATE INDEX IF NOT EXISTS idx_people_name ON people(name);
CREATE INDEX IF NOT EXISTS idx_people_birth_year ON people(birth_year);

CREATE INDEX IF NOT EXISTS idx_places_name ON places(name);
CREATE INDEX IF NOT EXISTS idx_places_type ON places(type);

CREATE INDEX IF NOT EXISTS idx_event_people_event ON event_people(event_id);
CREATE INDEX IF NOT EXISTS idx_event_people_person ON event_people(person_id);

CREATE INDEX IF NOT EXISTS idx_event_places_event ON event_places(event_id);
CREATE INDEX IF NOT EXISTS idx_event_places_place ON event_places(place_id);

-- Full-text search (SQLite FTS5)
CREATE VIRTUAL TABLE IF NOT EXISTS events_fts USING fts5(
    title,
    description,
    content=events,
    content_rowid=id
);

-- Triggers to keep FTS in sync
CREATE TRIGGER IF NOT EXISTS events_fts_insert AFTER INSERT ON events BEGIN
    INSERT INTO events_fts(rowid, title, description)
    VALUES (new.id, new.title, new.description);
END;

CREATE TRIGGER IF NOT EXISTS events_fts_delete AFTER DELETE ON events BEGIN
    DELETE FROM events_fts WHERE rowid = old.id;
END;

CREATE TRIGGER IF NOT EXISTS events_fts_update AFTER UPDATE ON events BEGIN
    DELETE FROM events_fts WHERE rowid = old.id;
    INSERT INTO events_fts(rowid, title, description)
    VALUES (new.id, new.title, new.description);
END;

-- Views for common queries
CREATE VIEW IF NOT EXISTS events_with_details AS
SELECT
    e.*,
    GROUP_CONCAT(DISTINCT p.name) as people_names,
    GROUP_CONCAT(DISTINCT pl.name) as place_names
FROM events e
LEFT JOIN event_people ep ON e.id = ep.event_id
LEFT JOIN people p ON ep.person_id = p.id
LEFT JOIN event_places epl ON e.id = epl.event_id
LEFT JOIN places pl ON epl.place_id = pl.id
GROUP BY e.id;

-- Timeline view (chronological order)
CREATE VIEW IF NOT EXISTS timeline AS
SELECT
    year,
    year_end,
    title,
    description,
    category,
    region,
    importance,
    source_page,
    CASE
        WHEN year < 0 THEN ABS(year) || ' př.n.l.'
        ELSE year || ' n.l.'
    END as year_display
FROM events
ORDER BY year ASC;
