# CMSD Extraction Scripts

Extraction pipeline pro zpracování historických PDF infografik.

---

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

**Dependencies:**
- `pdf2image` - PDF → Image conversion
- `Pillow` - Image processing
- `anthropic` - Claude AI API
- `pandas` - Data export

**System Requirements:**
- Python 3.8+
- Poppler (for pdf2image)

**Install Poppler:**

**Windows:**
```bash
# Download from: https://github.com/oschwartz10612/poppler-windows/releases
# Extract and add bin/ to PATH
```

**macOS:**
```bash
brew install poppler
```

**Linux:**
```bash
sudo apt-get install poppler-utils
```

---

### 2. Configure API Key

Create `.env` file:

```bash
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY
```

Or export directly:

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
```

---

## Usage

### Step 1: Extract Events from PDFs

```bash
python scripts/extract.py
```

**What it does:**
1. Converts each PDF to image (150 DPI)
2. Sends image to Claude Vision API
3. Extracts structured events (JSON)
4. Saves per-PDF results: `data/processed/{filename}_events.json`
5. Saves combined results: `data/processed/all_events.json`
6. Generates stats: `data/processed/extraction_stats.json`

**Expected output:**
```
CMSD Historical Timeline Data Extraction
============================================================
Found 19 PDF files to process

============================================================
Processing: 1L.pdf
============================================================
Converting 1L.pdf to image...
  Image size: 3.45 MB
Extracting events from 1L...
  ✓ Extracted 47 events
✓ Saved to 1L_events.json

[...continues for all PDFs...]

============================================================
EXTRACTION COMPLETE
============================================================
Total PDFs: 19
Processed: 19
Total events extracted: 1247
Errors: 0

Combined results saved to: all_events.json
```

---

### Step 2: Populate Database

```bash
python scripts/database.py
```

**What it does:**
1. Creates SQLite database: `data/database/cmsd.db`
2. Loads `all_events.json`
3. Inserts events, people, places
4. Creates relations (event-people, event-places)
5. Exports CSVs: `events.csv`, `people.csv`, `places.csv`, `timeline.json`

**Expected output:**
```
Populating database with 1247 events...
  Processed 50/1247 events...
  Processed 100/1247 events...
  [...]

============================================================
DATABASE POPULATION COMPLETE
============================================================
Events: 1247
People: 213
Places: 87
Relations: 845

Exporting to CSV...
✓ Exported 1247 events to events.csv
✓ Exported 213 people to people.csv
✓ Exported 87 places to places.csv
✓ Exported 1247 timeline entries to timeline.csv
✓ Exported timeline to timeline.json
```

---

## Output Files

### JSON Outputs

```
data/processed/
├── 1L_events.json              # Events from 1L.pdf
├── 1R_events.json              # Events from 1R.pdf
├── [...]
├── all_events.json             # Combined events (ALL PDFs)
└── extraction_stats.json       # Extraction statistics
```

### Database

```
data/database/
├── schema.sql                  # Database schema
└── cmsd.db                     # SQLite database
```

### CSV Exports

```
data/processed/
├── events.csv                  # All events
├── people.csv                  # All people
├── places.csv                  # All places
├── timeline.csv                # Timeline view
└── timeline.json               # Timeline JSON
```

---

## Event Structure

Each extracted event has this structure:

```json
{
  "year": -608,
  "year_end": -538,
  "title": "Babylónská říše",
  "description": "Zlatá hlava a lev představují Babylónskou říši...",
  "category": "politics",
  "region": "Blízký východ",
  "importance": 5,
  "tags": ["babylon", "říše", "nabuchodonosor"],
  "people": ["Nabuchodonozor"],
  "places": ["Babylón"],
  "bible_refs": ["Daniel 7:4"],
  "source_page": "zadniPredsRub"
}
```

**Fields:**
- `year` - Rok (záporné = př.n.l., kladné = n.l.)
- `year_end` - Konec období (NULL = single event)
- `title` - Název události
- `description` - Detailní popis
- `category` - religion/war/politics/discovery/culture/science
- `region` - Geografická oblast
- `importance` - 1-5 (5 = highest)
- `tags` - Klíčová slova
- `people` - Zmíněné osoby
- `places` - Zmíněná místa
- `bible_refs` - Biblické odkazy
- `source_page` - Source PDF (bez .pdf extension)

---

## Troubleshooting

### Error: "ANTHROPIC_API_KEY not set"

```bash
export ANTHROPIC_API_KEY="your_key_here"
# Or create .env file
```

### Error: "pdf2image not working"

Install Poppler (see Setup section above).

### Error: "Image too large"

Edit `extract.py` and lower DPI:

```python
images = convert_from_path(str(pdf_path), dpi=100)  # Lower from 150
```

### Low extraction quality

- Increase DPI for better OCR
- Check PDF quality (some pages may be scanned poorly)
- Review extracted JSON and manually fix if needed

---

## Customization

### Adjust Extraction Prompt

Edit `extract.py`, function `extract_events_from_image()`:

```python
prompt = f"""Your custom prompt here..."""
```

### Change Image DPI

```python
img_base64 = pdf_to_base64_image(pdf_path, dpi=200)  # Higher quality
```

### Process Subset of PDFs

```python
# In extract.py, filter PDFs:
pdf_files = [f for f in pdf_files if '1L' in f.name or '1R' in f.name]
```

---

## Performance

**Extraction time:**
- ~30-60 seconds per PDF (depends on API response time)
- Total for 19 PDFs: ~15-30 minutes

**Database population:**
- <1 minute for 1000+ events

**Cost estimate:**
- Claude Sonnet 4.5 Vision: ~$3-5 per 1M tokens
- 19 PDFs ≈ 500K tokens ≈ $2-3 total

---

## Next Steps

After extraction:

1. **Review data quality** - Check `all_events.json`
2. **Query database** - `sqlite3 data/database/cmsd.db`
3. **Export for mobile app** - Use CSVs or JSON
4. **Create MCP server** - For AI-powered queries
5. **Build visualizations** - Timeline charts, maps

---

Last updated: January 2026
