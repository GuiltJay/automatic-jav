# JAV.guru Data Hub

A fully automated **web scraping, data processing, and static site generation** pipeline. Scrapes content from multiple sources, extracts HLS video streams, deduplicates data, and publishes a browsable static site to **GitHub Pages** — all running daily via GitHub Actions inside Docker.

---

## Features

- **Multi-source scraping**: JAV.guru (async + Cloudflare bypass), MissAV (category + code-based), OneJAV (torrent aggregation)
- **HLS stream extraction**: Decodes obfuscated JavaScript (`p,a,c,k,e,d` packer) to extract M3U8 playlist URLs
- **Cross-pipeline integration**: JAV.guru codes are automatically looked up on MissAV for stream matching
- **Smart deduplication**: Already-processed codes are skipped using `missav.json` as source of truth (case-insensitive)
- **Source tagging**: Each MissAV entry is tagged as `jav.guru` or `category` based on origin
- **Inline video player**: HLS.js-powered playback with quality selection (1080p/720p/480p) on both Home and MissAV pages
- **Sticky mini player**: Follows scroll with time sync between inline and mini player
- **Static-first architecture**: All pages are self-contained HTML with embedded data — zero backend
- **Daily automation**: GitHub Actions cron + Docker container
- **GitHub Pages deployment**: Served from `docs/` directory

---

## Project Structure

```
.
├── Dockerfile                 # Container (based on crawl4ai image)
├── run_pipeline.sh            # JAV.guru pipeline orchestrator
├── missav_pipeline.sh         # MissAV pipeline orchestrator
├── onejav_pipeline.sh         # OneJAV pipeline orchestrator
├── requirements.txt           # Python dependencies
│
├── scripts/
│   ├── scraper.py             # Async JAV.guru scraper (crawl4ai + aiohttp)
│   ├── passvie_scraper.py     # Legacy sync JAV.guru scraper (cloudscraper)
│   ├── missav.py              # MissAV scraper + JS unpacker + M3U8 extractor
│   ├── dupe_filter.py         # CSV deduplication and URL normalization
│   ├── build_index.py         # Generates home.html (with MissAV stream pills)
│   ├── build_codes.py         # Generates codes.html + codes.txt
│   ├── build_sitemap.py       # Generates sitemap.html
│   ├── build_missav.py        # Generates missav.html + missav.json (with source tags)
│   ├── onejav.py              # OneJAV scraper (cloudscraper, torrent aggregation)
│   └── build_onejav.py        # Generates onejav.html + onejav.json (with source tags)
│
├── docs/                      # GitHub Pages output
│   ├── index.html             # Landing page with navigation
│   ├── home.html              # Thumbnail grid + inline HLS player
│   ├── codes.html             # Searchable code index
│   ├── codes.txt              # Plain-text code list (used by MissAV scraper)
│   ├── sitemap.html           # Full URL sitemap with filtering
│   ├── missav.html            # MissAV video browser + HLS player
│   ├── missav.json            # MissAV data feed (structured, tagged)
│   ├── onejav.html            # OneJAV torrent browser
│   └── onejav.json            # OneJAV data feed (structured, tagged)
│
├── results/
│   ├── raw/                   # Daily JAV.guru CSV snapshots
│   ├── raw_missav/            # Daily MissAV CSV + JSON snapshots
│   ├── raw_onejav/            # Daily OneJAV CSV + JSON snapshots
│   └── processed/
│       ├── combined.csv       # Deduplicated JAV.guru master dataset
│       ├── missav.csv         # Deduplicated MissAV master dataset
│       └── onejav.csv         # Deduplicated OneJAV master dataset
│
└── .github/workflows/
    ├── main.yaml              # Combined daily pipeline (JAV + MissAV)
    ├── jav.yaml               # Standalone JAV.guru pipeline (manual)
    └── missav.yml             # Standalone MissAV pipeline (manual)
```

---

## Pipeline Flow

### JAV.guru Pipeline (`run_pipeline.sh`)

```
scraper.py          → results/raw/jav_links_YYYY-MM-DD_HHMMSS.csv
       │
dupe_filter.py      → results/processed/combined.csv
       │
build_index.py      → docs/home.html        (+ loads missav.json for stream pills)
build_codes.py      → docs/codes.html + docs/codes.txt
build_sitemap.py    → docs/sitemap.html
```

### MissAV Pipeline (`missav_pipeline.sh`)

```
missav.py           → results/raw_missav/Missav_links_YYYY-MM-DD.csv/.json
                    → results/processed/missav.csv
       │
build_missav.py     → docs/missav.html + docs/missav.json  (tagged: jav.guru / category)
```

### OneJAV Pipeline (`onejav_pipeline.sh`)

```
onejav.py           → results/raw_onejav/onejav_YYYY-MM-DD.csv/.json
                    → results/processed/onejav.csv
       │
build_onejav.py     → docs/onejav.html + docs/onejav.json  (tagged: jav.guru / new)
```

### Cross-Pipeline Data Flow

```
JAV pipeline                          MissAV pipeline
───────────                           ────────────────
combined.csv ──► build_codes.py       missav.py reads:
                      │                 ├── docs/codes.txt    (new codes to look up)
                      ▼                 └── docs/missav.json  (already processed, skip)
               docs/codes.txt ───────►
                                      build_missav.py reads:
               docs/missav.json ◄────   ├── missav.csv        (stream data)
                      │                 └── docs/codes.txt    (for jav.guru/category tagging)
                      ▼
               build_index.py         home.html cards get stream pills
               (loads missav.json)    if matching code found in missav.json
```

---

## Pages Overview

### `index.html` — Landing Page
Static navigation page with links to all sections.

### `home.html` — Home
- Thumbnail grid with pagination (20/page)
- Inline HLS video player with quality pills (1080p / 720p / 480p / playlist)
- Preview pill for MP4 previews
- Stream count badge per card
- Date added badge
- Source page link
- Client-side search by URL or code
- Sticky mini player with time sync

### `missav.html` — MissAV Browser
- Virtual scroll for 16,000+ video cards
- Source tag on each card: **JAV.guru** (blue) or **Category** (purple)
- Quality pills with HLS.js playback
- Preview button for MP4 previews
- Click thumbnail to auto-play best available stream
- Sticky mini player with close button
- Search by code or tag (type "jav.guru" or "category")

### `onejav.html` — OneJAV Browser
- Virtual scroll for torrent cards
- Source tag on each card: **JAV.guru** (blue) if code exists in `codes.txt`, otherwise **New**
- Thumbnail, file size badge, date badge
- Actress name and content tags (up to 5 shown)
- Torrent download button per card
- Search by code, actress, tag, or title

### `codes.html` — Code Index
- Responsive grid of clickable code chips
- Search and click-to-copy
- Plain-text export (`codes.txt`)

### `sitemap.html` — Sitemap
- Full URL list with dates and domains
- Client-side filtering

---

## Tech Stack

| Component | Technology |
|---|---|
| Language | Python 3 |
| Scraping | crawl4ai, aiohttp, cloudscraper, BeautifulSoup |
| Video | HLS.js (CDN), custom JS unpacker for M3U8 extraction |
| Container | Docker (base: `ghcr.io/guiltjay/crawl4ai:latest`) |
| CI/CD | GitHub Actions (daily cron + manual triggers) |
| Hosting | GitHub Pages (from `docs/`) |
| Image Proxy | Cloudflare Worker (`imgproxy.mrspidyxd.workers.dev`) |

---

## Quick Start

### Run locally

```bash
chmod +x run_pipeline.sh missav_pipeline.sh onejav_pipeline.sh

# JAV.guru pipeline
./run_pipeline.sh

# MissAV pipeline (run after JAV pipeline for cross-referencing)
./missav_pipeline.sh

# OneJAV pipeline (independent, can run anytime)
./onejav_pipeline.sh
```

### Run via Docker

```bash
docker build -t scraper-pipeline .

# JAV pipeline
docker run --rm \
  -v "$(pwd)/docs:/app/docs" \
  -v "$(pwd)/results:/app/results" \
  scraper-pipeline

# MissAV pipeline
docker run --rm \
  -v "$(pwd)/docs:/app/docs" \
  -v "$(pwd)/results:/app/results" \
  scraper-pipeline bash missav_pipeline.sh

# OneJAV pipeline
docker run --rm \
  -v "$(pwd)/docs:/app/docs" \
  -v "$(pwd)/results:/app/results" \
  scraper-pipeline bash onejav_pipeline.sh
```

---

## GitHub Pages Setup

1. Go to **Repository > Settings > Pages**
2. Source: Branch `main`, Folder `/docs`
3. Save

Site will be available at `https://<username>.github.io/<repo>/`

---

## How Deduplication Works

### JAV.guru (`dupe_filter.py`)
- Normalizes URLs (lowercase scheme/host, strip tracking params, sort query params)
- Deduplicates on `normalized_page_url`, keeping newest row per URL

### MissAV (`missav.py`)
- Reads `docs/missav.json` to get already-processed codes (source of truth)
- Case-insensitive comparison (`AARM-317` matches `aarm-317`)
- Skips codes already in `missav.json` from both category scraping and guru code lookup
- Codes that were fetched but yielded no playlists are automatically retried on next run

### Date Added
- Derived from raw CSV filenames: `jav_links_2025-12-28_181113.csv` → `2025-12-28`
- Earliest file containing a URL determines its "date added"
- Stable across rebuilds

---

## Data Scale

| Dataset | Records |
|---|---|
| `combined.csv` | ~16,500 unique JAV.guru URLs |
| `missav.csv` | ~43,800 playlist entries |
| `missav.json` | ~16,800 videos (tagged) |
| `codes.txt` | ~15,700 unique codes |
| `onejav.csv` | ~69 torrent entries (7-day rolling window) |

---

## TODO

- [ ] **Add javct.com scraper** — New source for content scraping and stream extraction
- [x] **Add onejav.com scraper** — Torrent/magnet link aggregation (done: scraper + build + pipeline)
- [ ] Add `robots.txt` and `sitemap.xml` for SEO
- [ ] Stats dashboard (growth over time, source breakdown)
- [ ] CSV/JSON export from sitemap page
- [ ] Dark/light theme toggle
- [ ] Rename `passvie_scraper.py` → `passive_scraper.py`
- [ ] Add automated tests

---

## License

This project is for **educational and research purposes**.
Use responsibly and comply with applicable laws and site terms.
