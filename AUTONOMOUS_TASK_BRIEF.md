# 🤖 AUTONOMOUS TASK: CMSD Historical Data Extraction

**For: Claude Code Terminal**  
**Mode: Full Autonomy** 🚀

---

## 📋 YOUR MISSION

Extract structured historical data from Czech PDF infographics into a PostgreSQL database.

**You have complete freedom on:**
- Architecture & approach
- Tools & libraries
- Database design
- Extraction methodology
- Quality assurance

**Just deliver the results!**

---

## 📁 INPUT FILES

```
/project/pdfs/
├── 1L.pdf, 1R.pdf          # Creation, flood (biblical)
├── 2L.pdf, 2R.pdf          # Biblical chronology
├── 3L.pdf, 3R.pdf          # Ancient history
├── 4L.pdf, 4R.pdf          # Classical antiquity
├── 5L.pdf, 5R.pdf          # Middle Ages
├── 6L.pdf, 6R.pdf          # Early modern
├── 7L.pdf, 7R.pdf          # Modern era
├── 8L.pdf, 8R.pdf          # Contemporary
├── PredniPreds.pdf         # Introduction
├── zadniPredsLic.pdf       # Ten Commandments
└── zadniPredsRub.pdf       # Daniel prophecy

/project/knowledge_cards/
├── cmsd_cards_batch1.jsonl
├── cmsd_cards_batch2.jsonl
├── cmsd_cards_batch3.jsonl
├── cmsd_cards_batch4.jsonl
└── cmsd_cards_batch5.jsonl
```

**19 PDFs + 5 JSONL files with metadata**

---

## 🎯 DELIVERABLES

### 0. GitHub Repository ⭐ NEW!
Create a new GitHub repository for this project:

**Repository Name:** `cmsd-historical-timeline`

**Description:** 
```
Chronologická mapa světových dějin (CMSD) - Digital Database

Structured historical timeline database extracted from Czech historical infographics. 
Contains 1000+ events from Creation to modern times, with people, places, and biblical references.

Mobile app coming soon (React Native)!
```

**Repository Structure:**
```
cmsd-historical-timeline/
├── README.md                  # Project overview, features, usage
├── data/
│   ├── raw/
│   │   ├── pdfs/             # Original 19 PDF infographics
│   │   └── knowledge_cards/  # Metadata JSONL files
│   ├── processed/
│   │   ├── events.csv
│   │   ├── people.csv
│   │   ├── places.csv
│   │   └── timeline.json
│   └── database/
│       ├── schema.sql
│       └── cmsd.db           # SQLite export
├── scripts/
│   ├── extract.py            # Main extraction pipeline
│   ├── ocr_utils.py
│   ├── llm_extraction.py
│   └── database.py
├── docs/
│   ├── EXTRACTION_REPORT.md  # Data quality & coverage
│   ├── DATABASE_SCHEMA.md    # Schema documentation
│   └── API.md                # Future API docs
├── .gitignore
└── LICENSE                    # MIT or appropriate license
```

**README.md should include:**
- Project description (Czech historical timeline database)
- Context: Part of CMSD mobile app project (React Native)
- Features: 1000+ events, searchable, AI-ready
- Data structure & schema
- Usage examples (SQL queries)
- Future: Mobile app, AI integration, MCP server
- Credits to original infographic author

**Commit everything with meaningful messages!**

### 1. Populated Database
PostgreSQL or SQLite with structured historical events:
- Events (year, title, description, category, region...)
- People (name, birth/death years, role...)
- Places (name, type, coordinates...)
- Relations (event-people, event-places...)
- Knowledge cards imported

### 2. Data Exports
- `events.csv` - All extracted events
- `people.csv` - All people
- `places.csv` - All places  
- `timeline.json` - Full timeline data

### 3. Quality Report
- `EXTRACTION_REPORT.md` with:
  - Events extracted per page
  - Coverage statistics
  - Issues encountered
  - Sample queries & results

### 4. Working Code
- Extraction scripts (Python/Node/whatever you choose)
- Database schema
- README with usage instructions

---

## ✅ SUCCESS CRITERIA

- **GitHub repository created** with proper structure
- **All source PDFs committed** to repo (data/raw/pdfs/)
- **Minimum 500 events** extracted (target: 1000-2000)
- **All 19 PDFs** processed
- **Czech encoding** preserved (UTF-8, diacritics intact)
- **BC/AD years** handled correctly (negative for BC)
- **Searchable database** (by year, person, place, tags)
- **Clean data** (<5% duplicates)
- **Documented** (clear README + extraction report)
- **Professional README** describing the CMSD mobile app project

---

## 💡 SUGGESTED APPROACH (Optional!)

You don't have to follow this - choose your own path!

**Option A: OCR + LLM Extraction**
1. pdf2image + Tesseract OCR (Czech lang)
2. GPT-4o/Claude for structured extraction
3. PostgreSQL for storage

**Option B: Direct Text Extraction**
1. PyMuPDF for text (faster if PDFs have text layer)
2. LLM extraction
3. Database population

**Option C: Vision + LLM**
1. Convert PDF to images
2. GPT-4o Vision for direct extraction
3. Skip OCR entirely!

**You decide!** Pick what works best.

---

## 🔧 TOOLS AT YOUR DISPOSAL

**PDF Processing:**
- pdf2image, PyMuPDF, pdfplumber
- Tesseract OCR (Czech support)
- Poppler utils

**LLM APIs:**
- OpenAI GPT-4o (vision + text)
- Anthropic Claude (Sonnet/Opus)
- Both available via API

**Database:**
- PostgreSQL (recommended)
- SQLite (simpler, portable)
- Whatever you prefer!

**Languages:**
- Python (recommended for data work)
- Node.js (if you prefer)
- Mix & match!

---

## 📊 DATA STRUCTURE HINTS

### Expected Event Format:
```json
{
  "year": -2348,              // Negative = BC
  "year_end": null,           // For periods
  "title": "Potopa světa",
  "description": "Biblická potopa za Noeho...",
  "category": "religion",     // war, discovery, politics...
  "region": "Blízký východ",
  "importance": 5,            // 1-5
  "tags": ["bible", "potopa", "noe"],
  "people": ["Noe"],
  "places": ["Ararat"],
  "bible_refs": ["Genesis 6-9"],
  "source_page": "2L"
}
```

### Knowledge Card Format:
```json
{
  "id": "cmsd_2019_2l",
  "doc_id": "2L",
  "title": "Noe a potopa světa",
  "summary": "Biblická chronologie...",
  "topics": ["bible", "potopa"],
  "entities": {
    "people": ["Noe"],
    "places": ["Ararat"],
    "events": ["Potopa světa"]
  }
}
```

Use knowledge cards for **context** when extracting!

---

## ⚠️ IMPORTANT NOTES

1. **Language:** PDFs are in Czech
   - OCR needs Czech language (`-l ces`)
   - LLM should understand Czech context
   - Preserve Czech characters (č, š, ž, ř, ů, ě, ý, á...)

2. **Year Format:**
   - BC (př.n.l.) = negative numbers: -2348
   - AD (n.l.) = positive numbers: 1492
   - Biblical chronology uses different systems - normalize!

3. **Knowledge Cards:**
   - Some have empty entities - that's OK!
   - Extract from OCR/vision instead
   - Use cards for validation & context

4. **PDF Quality:**
   - May vary between pages
   - Implement fallback strategies
   - Test on 1-2 pages first!

---

## 🚀 EXECUTION PLAN

**You're autonomous! But here's a suggested flow:**

### Phase 1: Reconnaissance (30 min)
- Examine input files
- Test OCR on sample PDF
- Choose extraction approach
- Design database schema

### Phase 2: Pipeline Development (2-3 hours)
- Build extraction pipeline
- Test on 2-3 PDFs
- Iterate & improve
- Scale to all 19 PDFs

### Phase 3: Database Population (30 min)
- Create schema
- Insert extracted data
- Build relations
- Add indexes

### Phase 4: Validation (30 min)
- Quality checks
- Generate statistics
- Export CSVs
- Write report

### Phase 5: Documentation (15 min)
- Write README
- Document approach
- Provide usage examples

**Total: ~4-5 hours of work**

---

## 🎯 AUTONOMOUS WORKFLOW

**I trust you to:**
1. ✅ Examine the inputs
2. ✅ Choose the best approach
3. ✅ Install needed dependencies
4. ✅ Build the pipeline
5. ✅ Handle errors gracefully
6. ✅ Validate results
7. ✅ Document everything
8. ✅ Deliver clean outputs

**Ask me ONLY if:**
- ❓ You need external resources (API keys, etc.)
- ❓ You hit a blocker you can't solve
- ❓ You need clarification on requirements

**Otherwise: GO FOR IT!** 💪

---

## 📈 PROGRESS REPORTING

Feel free to report progress at key milestones:

```
✅ Phase 1 complete: Tested OCR on 1L.pdf
   → Extracted 45 events
   → Quality: Good
   → Approach: GPT-4o Vision

✅ Phase 2 complete: All PDFs processed
   → Total: 1,247 events extracted
   → 213 people, 87 places
   → Issues: 3 PDFs had low quality (handled)

✅ Phase 3 complete: Database populated
   → PostgreSQL schema created
   → All data inserted
   → Indexes added

✅ Phase 4 complete: Validation done
   → Quality: 97% (38 duplicates removed)
   → Coverage: All pages processed
   → CSVs exported

✅ DONE! See EXTRACTION_REPORT.md
```

---

## 🎁 BONUS POINTS (Optional)

If you have time/interest:

- 🌟 Create MCP server for querying the database
- 🌟 Add full-text search indexes
- 🌟 Generate sample visualizations (timeline chart)
- 🌟 Create API endpoints for the data
- 🌟 Build simple web UI for browsing

**But main deliverables come first!**

---

## 🏁 READY?

You have:
- ✅ Clear objective
- ✅ Input files
- ✅ Success criteria  
- ✅ Full autonomy
- ✅ All the tools you need

**Now go build something awesome!** 🚀

---

## 📞 CONTACT

If you need me:
- Ask questions anytime
- Share progress when you want
- Request clarifications if needed

Otherwise: **I trust you to deliver!** 💪

**Good luck, Claude Code!** 🎯
