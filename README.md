# 📊 JAV.guru Data Pipeline & Static Site

A fully automated **CSV scraping → deduplication → aggregation → static website** pipeline, optimized for **GitHub Pages**.

This project collects daily CSV snapshots, processes them into a unified dataset, and publishes a fast, static browsing interface (Home, Codes, Sitemap).

---

## ✨ Features

* 🕷️ Automated scraping into timestamped CSV files
* 🧹 Deduplication and normalization of URLs
* 📦 Unified `combined.csv` dataset
* 🗓️ Accurate **first-seen “date added”** for every post
* 🏠 Modern Home page with thumbnails and pagination
* 🏷️ Codes index (content codes extracted from URLs)
* 🗺️ Sitemap with dates, domains, and filtering
* 🚀 One-command pipeline
* 🌐 GitHub Pages–ready static site

---

## 📁 Project Structure

```
.
├── README.md
├── run_pipeline.sh
├── docs/                  # GitHub Pages output
│   ├── index.html         # Static landing page
│   ├── home.html          # Main grid view
│   ├── codes.html         # Extracted codes
│   └── sitemap.html       # Full URL sitemap
├── results/
│   ├── raw/               # Daily raw CSV snapshots
│   │   └── jav_links_YYYY-MM-DD_HHMMSS.csv
│   └── processed/
│       └── combined.csv   # Deduplicated master dataset
└── scripts/
    ├── scraper.py         # Scraper → results/raw/
    ├── dupe_filter.py     # Optional cleanup
    ├── build_index.py     # Build combined.csv
    ├── build_home.py      # Build docs/home.html
    ├── build_codes.py     # Build docs/codes.html
    └── build_sitemap.py   # Build docs/sitemap.html
```

---

## 🚀 Quick Start

### 1️⃣ Make pipeline executable

```bash
chmod +x run_pipeline.sh
```

### 2️⃣ Run everything

```bash
./run_pipeline.sh
```

This will:

* Scrape new data (if enabled)
* Deduplicate and normalize
* Build `results/processed/combined.csv`
* Generate all HTML pages in `docs/`

---

## 🌐 GitHub Pages Setup

1. Go to **Repository → Settings → Pages**
2. Source:

   * Branch: `main`
   * Folder: `/docs`
3. Save

Your site will be available at:

```
https://<username>.github.io/<repo>/
```

---

## 🏠 Pages Overview

### 📍 `index.html`

Static landing page with large navigation buttons:

* Home
* Codes
* Sitemap

### 🏠 `home.html`

* Grid layout with thumbnails
* Pagination (20 per page)
* Displays **date added** (first seen)
* Client-side filtering

### 🏷️ `codes.html`

* Unique content codes extracted from URLs
* Clean, copy-friendly layout

### 🗺️ `sitemap.html`

* Full list of URLs
* First-seen date
* Domain shown
* Live filter

---

## 🗓️ How “Date Added” Works

* Dates are derived from **raw CSV filenames**:

  ```
  jav_links_2025-12-28_181113.csv → 2025-12-28
  ```
* The **earliest file** containing a URL determines its “date added”
* This ensures stable, meaningful timestamps across rebuilds

---

## 🔁 Pipeline Flow

```
scraper.py
   ↓
results/raw/*.csv
   ↓
dupe_filter.py (optional)
   ↓
build_index.py
   ↓
results/processed/combined.csv
   ↓
build_home.py     → docs/home.html
build_codes.py    → docs/codes.html
build_sitemap.py  → docs/sitemap.html
```

---

## 🧠 Design Principles

* **Static-first** (no backend required)
* **Deterministic builds** (same input → same output)
* **Fast load times**
* **GitHub Pages compatible**
* **Minimal dependencies**
* **Human-readable data**

---

## 📌 Notes

* CSV files in `results/raw/` are not exposed publicly
* Only files in `docs/` are served by GitHub Pages
* All filtering/search is client-side JavaScript
* Safe to re-run pipeline at any time

---

## 🔮 Possible Enhancements

* GitHub Actions for scheduled runs
* `robots.txt` + `sitemap.xml`
* CSV export from sitemap
* Tagging / categorization
* Dark/light theme toggle
* Stats dashboard (growth over time)

---

## 📝 License

This project is for **educational and research purposes**.
Use responsibly and comply with applicable laws and site terms.
