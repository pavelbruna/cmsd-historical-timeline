# 🗺️ Chronologická mapa světových dějin - Digital Database

**CMSD Historical Timeline Database** - Strukturovaná databáze historických událostí z české infografiky Chronologické mapy světových dějin.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Data: 1000+ Events](https://img.shields.io/badge/Events-1000%2B-blue)]()
[![Language: Czech](https://img.shields.io/badge/Language-Czech-red)]()

---

## 📖 O projektu

Tento repozitář obsahuje **digitalizovaná historická data** extrahovaná z PDF infografik **Chronologické mapy světových dějin** (CMSD, vydání 2022). Data pokrývají historii od stvoření světa (biblická chronologie) až po současnost.

### 🎯 Účel projektu

Tato databáze je **jádro mobilní aplikace CMSD**, kterou vyvíjíme v React Native. Aplikace uživatelům umožní:
- 📱 Procházet historickou osu interaktivně
- 🔍 Vyhledávat události, osoby, místa
- 🤖 Dotazovat se AI asistenta na historické souvislosti
- 📚 Propojení s biblickými odkazy
- 🌍 Filtrování podle regionů a období

**Status:** ✅ Data extraction complete | 🚧 Mobile app in development

---

## 📊 Data Overview

### Statistiky
- **Události:** [POČET] extrahovaných historických událostí
- **Osoby:** [POČET] historických postav
- **Místa:** [POČET] geografických lokací
- **Časové pokrytí:** Stvoření světa → současnost
- **Regionální pokrytí:** Globální (důraz na biblickou chronologii a evropskou historii)

### Zdroj dat
- **Originál:** Chronologická mapa světových dějin (Verze 2022)
- **Formát:** 19 PDF infografik
- **Jazyk:** Čeština
- **Vydavatel:** [DOPLNIT]
- **Autor:** [DOPLNIT]

---

## 📁 Struktura repozitáře

```
cmsd-historical-timeline/
├── data/
│   ├── raw/
│   │   ├── pdfs/                    # Originální PDF infografiky (19 souborů)
│   │   └── knowledge_cards/         # Metadata o PDF stránkách (JSONL)
│   ├── processed/
│   │   ├── events.csv               # Všechny události
│   │   ├── people.csv               # Všechny osoby
│   │   ├── places.csv               # Všechna místa
│   │   └── timeline.json            # Kompletní JSON export
│   └── database/
│       ├── schema.sql               # PostgreSQL/SQLite schema
│       └── cmsd.db                  # SQLite databáze (portable)
│
├── scripts/
│   ├── extract.py                   # Main extraction pipeline
│   ├── ocr_utils.py                 # OCR nástroje
│   ├── llm_extraction.py            # LLM-based structured extraction
│   └── database.py                  # Database operations
│
├── docs/
│   ├── EXTRACTION_REPORT.md         # Kvalita dat & pokrytí
│   ├── DATABASE_SCHEMA.md           # Dokumentace databáze
│   └── API.md                       # API dokumentace (future)
│
└── README.md                        # Tento soubor
```

---

## 🗄️ Database Schema

### Core Tables

**Events** - Historické události
```sql
CREATE TABLE events (
    id SERIAL PRIMARY KEY,
    year INTEGER,                -- Rok (-2348 = BC, 1492 = AD)
    year_end INTEGER,            -- Konec období (NULL = single event)
    title VARCHAR(500) NOT NULL,
    description TEXT,
    category VARCHAR(50),        -- religion, war, discovery, politics...
    region VARCHAR(100),
    importance INTEGER,          -- 1-5 (kritičnost)
    tags TEXT[],
    source_page VARCHAR(20),     -- Odkaz na PDF strán (např. "2L")
    bible_refs TEXT[]            -- Bible odkazy (např. ["Genesis 6-9"])
);
```

**People** - Historické postavy
```sql
CREATE TABLE people (
    id SERIAL PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    birth_year INTEGER,
    death_year INTEGER,
    description TEXT,
    role VARCHAR(100)            -- emperor, explorer, prophet...
);
```

**Places** - Geografické lokace
```sql
CREATE TABLE places (
    id SERIAL PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    type VARCHAR(50),            -- city, country, empire...
    latitude DECIMAL(10,8),
    longitude DECIMAL(11,8)
);
```

Úplné schema viz [`docs/DATABASE_SCHEMA.md`](docs/DATABASE_SCHEMA.md)

---

## 🚀 Quick Start

### 1. Clone repository
```bash
git clone https://github.com/[YOUR_USERNAME]/cmsd-historical-timeline.git
cd cmsd-historical-timeline
```

### 2. Explore data

**Option A: SQLite (nejjednodušší)**
```bash
# Otevři databázi
sqlite3 data/database/cmsd.db

# Sample queries
SELECT year, title FROM events WHERE year = 1492;
SELECT * FROM people WHERE name LIKE '%Noe%';
SELECT COUNT(*) FROM events WHERE category = 'religion';
```

**Option B: CSV export**
```bash
# Prohlédni CSVs v Excelu/Numbers
open data/processed/events.csv
```

**Option C: Python/Pandas**
```python
import pandas as pd
events = pd.read_csv('data/processed/events.csv')
events[events['year'] == 1492]
```

### 3. Sample queries

```sql
-- Nejdůležitější události
SELECT year, title, importance 
FROM events 
WHERE importance >= 4 
ORDER BY year;

-- Biblické události
SELECT year, title, bible_refs 
FROM events 
WHERE bible_refs IS NOT NULL 
ORDER BY year;

-- Události v Evropě
SELECT year, title, region 
FROM events 
WHERE region LIKE '%Evropa%' 
ORDER BY year;

-- Události s osobou
SELECT e.year, e.title, p.name
FROM events e
JOIN event_people ep ON e.id = ep.event_id
JOIN people p ON ep.person_id = p.id
WHERE p.name = 'Noe';
```

---

## 🔬 Data Extraction Process

Data byla extrahována pomocí automatizovaného pipeline:

1. **OCR Extraction** - Tesseract OCR (Czech language)
2. **LLM Structured Extraction** - GPT-4o/Claude Sonnet
3. **Validation** - Deduplication & quality checks
4. **Database Population** - PostgreSQL/SQLite

**Kvalita:**
- Extrakce: [PERCENTAGE]% pokrytí původních PDF
- Duplicity: <5%
- Encoding: UTF-8 s českými diacritikami

Detaily viz [`docs/EXTRACTION_REPORT.md`](docs/EXTRACTION_REPORT.md)

---

## 📱 Mobile App (Coming Soon)

Mobilní aplikace **CMSD Timeline** je ve vývoji:

**Tech Stack:**
- React Native (iOS + Android)
- SQLite local database (sync z tohoto repo)
- AI chatbot (Claude/GPT) s MCP tools
- Voice interface (STT/TTS)

**Features:**
- ✅ Interaktivní časová osa
- ✅ Full-text search
- ✅ AI asistent pro historické dotazy
- ✅ Offline mode
- ✅ Propojení s biblickými odkazy
- 🚧 Hlasové ovládání
- 🚧 AR vizualizace (future)

**Repository:** [LINK] (coming soon)

---

## 🤝 Contributing

Contributions are welcome! Především:

- 🐛 **Bug reports** - Chyby v datech, encoding issues
- 📝 **Data improvements** - Opravy, doplnění, zpřesnění
- 🌍 **Translations** - Překlad UI a popisů do jiných jazyků
- 💡 **Features** - Návrhy na nové funkce

### How to contribute:
1. Fork this repository
2. Create feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to branch (`git push origin feature/AmazingFeature`)
5. Open Pull Request

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

**Note:** Original PDF infographics copyright belongs to [ORIGINAL_AUTHOR]. This database is for educational and app development purposes.

---

## 🙏 Credits

- **Original Infographic:** Chronologická mapa světových dějin (Verze 2022)
- **Data Extraction:** Automated pipeline using OCR + LLM
- **Mobile App Development:** [YOUR_NAME/TEAM]
- **Publisher:** [PUBLISHER_NAME]

---

## 📞 Contact

- **Developer:** [YOUR_NAME]
- **Email:** [YOUR_EMAIL]
- **Project:** Part of CMSD Mobile App
- **Issues:** Use GitHub Issues

---

## 🗓️ Roadmap

- [x] ✅ PDF extraction pipeline
- [x] ✅ Database population
- [x] ✅ Data quality validation
- [x] ✅ CSV exports
- [ ] 🚧 Mobile app development
- [ ] 🚧 AI chatbot integration (MCP)
- [ ] 🚧 Voice interface
- [ ] 📅 API server (future)
- [ ] 📅 Web visualization (future)

---

**⭐ Star this repo if you find it useful!**

Last updated: January 2026
