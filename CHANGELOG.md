# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [2.0.0] - 2026-09-04

### Added
- **Astro Static Site Architecture (`app/`)**:
  - Replaced legacy monolithic Jinja2 HTML shells (~35MB each) with an Astro v7 + Tailwind CSS v4 + TypeScript static site generator emitting directly to `docs/`.
  - Implemented **Archive-Console** design system with custom theme tokens: Ink (`#0C1013`), Archive Paper (`#F4F0E8`), Slate (`#141A1F`), Signal Cyan (`#00A7B5`), and Warning Amber (`#D99019`).
  - Added persistent **Archive Rail** displaying live dataset metrics, source distribution totals, and pipeline freshness.
  - Added global **Command Palette** modal (`Cmd+K` / `Ctrl+K`, `/`, `Esc`) for rapid keyboard navigation across sources, codes, models, and telemetry.
  - Added dedicated **Hls.js Video Player Island**: modal video player with native HLS support, error boundaries, and direct source fallbacks.
  - Created dedicated static pages:
    - `/index.html`: Overview telemetry dashboard with key KPI statistics and recent additions.
    - `/browse.html`: Unified multi-source catalogue with 150ms debounced search, source filter chips, sort controls, deep links, and chunked pagination (50 items/page).
    - `/codes.html`: Searchable code directory with one-click clipboard copying.
    - `/models.html`: Model and actress index with image fallbacks and view counters.
    - `/stats.html`: Telemetry page with responsive SVG timeline charts and source volume breakdown.
    - `/sitemap.html`: Paginated URL directory with one-click exports for raw JSON and CSV data.
  - Added directory alias mirrors (`docs/browse/index.html`, `docs/codes/index.html`, etc.) for seamless static routing parity across all host configurations.
  - Added backward-compatible transparent redirect routes: `/home.html`, `/missav.html`, `/onejav.html`, and `/javct.html`.
- **Automated Verification Suite (`tests/test_ui.py`)**:
  - Headless Chromium Playwright test suite integrated with pytest runner and session-scoped HTTP server fixtures, validating navigation, directory aliases, command palette shortcuts, theme toggling, card rendering, filtering, player island lifecycle, and responsive layouts down to 375px viewport with zero horizontal overflow.
- **Export Feeds & Compact Feeds**:
  - Added `docs/catalogue.json` compact feed builder (`scripts/build_catalogue.py`), reducing client browse payload from ~19MB down to ~1MB.
  - Added `docs/sitemap_preview.json` (~93KB) for instant initial sitemap rendering alongside full exports for `docs/sitemap.json` and `docs/sitemap_export.csv`.

### Changed
- **Build Output Optimization**:
  - Reduced individual page DOM node count from 64,000+ elements down to lightweight client-rendered chunks, dropping HTML page weight from 35MB+ to ~25-40KB per page.
  - Added automated build pipeline lifecycle (`prebuild.mjs`, `astro build`, `postbuild.mjs`) to mirror directory routes and prevent duplicate data storage in `app/public/`.
- **CI/CD Pipeline (`.github/workflows/main.yaml`, `.github/workflows/jav.yaml`)**:
  - Removed `continue-on-error: true` across all scraper steps, enforcing fail-fast data pipeline execution.
  - Added automated data integrity verification step validating generated CSV, JSON, and code files before frontend building.
  - Added automated Playwright test execution step in CI prior to deployment.
  - Added Astro build and routing alias generation steps to both primary workflows.
  - Replaced fragile globbing (`git add docs/*.html results/**/*.csv || true`) with deterministic directory staging (`git add docs results`).
  - Pinned exact action versions: `actions/checkout@v4.2.2`, `actions/setup-node@v4.2.0`, `actions/setup-python@v5.4.0`, and `peaceiris/actions-gh-pages@v4.0.0`.
  - Pinned Node runtime to exact version `22.14.0`.
- **Payload & Asset Optimization**:
  - Minified large JSON export feeds (`scripts/build_missav.py` and `scripts/build_sitemap.py`) using `separators=(',', ':')`, shrinking `missav.json` from 15.6MB to 11MB and `sitemap.json` from 14MB to 8.4MB.
  - Pinned `hls.js` to exact version `1.7.2` across npm and runtime scripts.
  - Configured local-first HLS distribution via `prebuild.mjs` (`docs/hls.min.js`), backed by a fallback CDN link with strict Subresource Integrity (`sha384-xZKOEqJSfUEI1E4N6MG1+KjnKYM1R1v2WKpyaS0c+ksIxRi5PB8MAkyEdX48MX2/`) and `crossorigin="anonymous"`.
- **Pipeline Shell Scripts (`run_pipeline.sh`, `aggregator_pipeline.sh`)**:
  - Added explicit directory context anchoring (`cd "$ROOT_DIR"`).
  - Reordered execution dependency chains to ensure `build_codes.py` runs before downstream stream consumers and `build_index.py` executes after scraper aggregation.
  - Added `scripts/build_catalogue.py` to the aggregator pipeline.
- **Dependency Pinning (`requirements.txt`, `Dockerfile`)**:
  - Strictly pinned Python dependencies to exact versions (`==`): `cloudscraper==1.2.71`, `beautifulsoup4==4.13.4`, `crawl4ai==0.4.248`, `aiohttp==3.14.3`, `lxml==6.1.3`, `jinja2==3.1.6`.
  - Strictly pinned Docker base image to exact SHA256 digest: `ghcr.io/guiltjay/crawl4ai:575087806e3a8a98512a44548ecef7865f4c6eb7@sha256:8935f76c0bb28f68d38e0d5c3ec37dfc7e5af0a505300ebfde639c726d07d4a9`.
- **Repository Ignore Rules (`.gitignore`)**:
  - Added ignore rules for `node_modules/`, `.astro/`, `app/dist/`, `app/public/*.{json,csv,txt,xml,js}`, and Playwright test screenshots.

### Fixed
- **Static Navigation Routing**:
  - Fixed relative links in `index.astro` and navigation headers to point directly to `.html` destinations, resolving 404 errors on static hosts.
- **XSS & Unsafe Markup Injection**:
  - Completely eliminated dynamic `innerHTML`, `outerHTML`, and string interpolation across `browse/index.astro`, `models/index.astro`, `stats/index.astro`, `codes/index.astro`, `sitemap/index.astro`, and `BaseLayout.astro`.
  - Replaced with safe DOM APIs (`document.createElement`, `replaceChildren`, `textContent`) and strict URL protocol validation (`safeUrl`).
- **Test Assertion Rigor (`tests/test_ui.py`)**:
  - Replaced ineffective assertion `assert page.locator("#cards-grid article").count() >= 0` with thorough search verification: checking initial count, verifying query substring containment in card elements, verifying empty state on non-matching queries, and verifying restored state after query clear.
- **Trailing Whitespace Errors**:
  - Cleared all trailing whitespace across generated HTML templates and `requirements.txt`, passing `git diff --check` with zero warnings.
- **Sitemap Generation Bug (`scripts/build_sitemap.py`)**:
  - Resolved critical bug where `sitemap.html` was rendered by Jinja but never written to disk.
- **Tag Matching Discrepancies**:
  - `scripts/build_onejav.py`: Implemented hyphen normalization for JAV.guru code formats, increasing matched tags from **0** to **2,732**.
  - `scripts/build_javct.py`: Implemented suffix stripping (`-RM`, `-SUB`, `-C`, `-4K`, etc.), increasing matched tags from **89** to **205**.
- **MissAV Scraper & Unpacker (`scripts/missav.py`)**:
  - Corrected Dean Edwards Base-62 character map lookup order (`0-9`, `a-z`, `A-Z`).
  - Improved code extraction regex to support leak and uncensored suffixes (`-uncensored-leak`).
- **Deterministic Deduplication (`scripts/dupe_filter.py`)**:
  - Replaced filesystem `mtime` sorting (unstable across CI checkouts) with deterministic filename sorting.
  - Added explicit `date_added` column preservation to `results/processed/combined.csv`.
- **HTTP Cookie Parsing**:
  - Fixed `cookies.update(res.cookies)` list-of-dicts crash in `scripts/scraper.py`, `scripts/javct.py`, and `scripts/onejav.py`.
- **Timezone Standardization**:
  - Replaced naive `datetime.now()` calls with `datetime.now(timezone.utc)` across `scripts/build_seo.py`, `scripts/build_sitemap.py`, `scripts/build_codes.py`, `scripts/build_index.py`, `scripts/scraper.py`, and `scripts/passive_scraper.py`.
- **Stats Builder (`scripts/build_stats.py`)**:
  - Fixed premature exit condition when processing CSV headers and resolved all lint warnings.

---

## [1.1.0] - 2026-07-16

### Added
- Multi-source scraper pipeline support for MissAV, OneJAV, and JavCT.
- Central aggregator pipeline combining source results into `results/processed/combined.csv`.

### Changed
- Refactored raw HTML generation into Jinja2 templates.
- Added automated daily GitHub Actions scheduled pipeline.

---

## [1.0.0] - 2026-07-13

### Added
- Initial release of automated JAV.guru link scraper.
- Markdown and basic static HTML generator for scraping results.
- GitHub Pages publishing workflow.
