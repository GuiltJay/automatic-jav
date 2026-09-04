# JAV.guru Web UI Redesign Plan

Status: implemented
Target: static GitHub Pages site
Repository: `MrSpidy32/automatic-jav`
Last reviewed: 2026-09-04

## 1. Product direction

### Product job

Turn the current collection of generated pages into a fast, calm, searchable
media catalogue. A visitor should be able to answer three questions quickly:

1. What was added recently?
2. Which source and quality are available for an item?
3. How do I narrow thousands of records without waiting for the browser?

### Proposed visual identity

Use an **archive-console** direction: a dark editorial catalogue inspired by
film indexes, signal monitors, and library accession records. The design should
feel like a carefully maintained research archive rather than a generic SaaS
dashboard.

Distinctive choices:

- A warm paper-white content surface against an ink-black shell, with one
  electric cyan signal color and one amber warning color.
- A display face with a slightly condensed character for page titles, paired
  with a highly legible sans-serif for controls and metadata.
- A persistent “archive rail” showing the current source, item count, and data
  freshness instead of a generic top navigation bar.
- Thin rules and small index marks only where they encode hierarchy or state.
- One memorable interaction: a keyboard-first command/search palette that can
  jump between sources, codes, models, and saved filters.

Avoid:

- Purple gradients, interchangeable rounded cards, excessive glassmorphism,
  and default Inter-only typography.
- Autoplay, infinite visual motion, and decorative badges with no meaning.
- Repeating every dataset as a giant page-sized JavaScript object when a
  route-level JSON feed will do.

## 2. Information architecture

```text
JAV.guru Archive
├── Overview                 /index.html
│   ├── Recent additions
│   ├── Source totals
│   ├── Stream availability
│   └── Freshness / pipeline status
├── Browse                   /browse/
│   ├── All
│   ├── JAV.guru
│   ├── MissAV
│   ├── OneJAV
│   └── JavCT
├── Codes                    /codes/
├── Models                   /models/
├── Statistics               /stats/
└── Sitemap / data exports   /sitemap/
```

### Page responsibilities

| Page | Primary task | Data strategy |
|---|---|---|
| Overview | Understand freshness and jump into browsing | Small summary JSON |
| Browse | Search, filter, sort, and play | Paginated/partitioned JSON |
| Codes | Find and copy a code | Sorted code index |
| Models | Browse model/actress records | Model JSON feed |
| Statistics | Understand source and date distribution | Aggregated stats JSON |
| Sitemap | Inspect every indexed URL | Generated CSV/JSON + HTML |

Each page must have a useful no-JavaScript fallback: heading, summary,
navigation, and links to the relevant data export. Interactive filtering and
video playback enhance the page but should not be the only way to discover it.

## 3. Proposed stack

### Recommended frontend

- **Astro + TypeScript** for static generation and shared layouts.
- **Vite** as the build tool and local preview server.
- **Tailwind CSS v4** through the official Vite plugin, with a small custom
  token layer for the archive-console visual language.
- **Native HTML elements first**: `<dialog>`, `<details>`, `<search>`,
  `<video>`, and accessible buttons before adding component abstractions.
- **Hls.js**, pinned to a tested version, loaded only on pages that need HLS.
- **Fuse.js** or a small indexed search worker for fuzzy code/title search.
- **@tanstack/virtual-core** only for genuinely large result sets; do not
  virtualize small pages.
- **uPlot** or a lightweight SVG chart layer for statistics; avoid loading a
  full chart framework on every browse page.
- **Zod** at the data boundary to validate generated JSON before build output.
- **Vitest** for pure data/URL/filter functions.
- **Playwright** for keyboard, filter, route, player, and responsive smoke
  tests.

Versions must be recorded in `package-lock.json` and updated deliberately.
“Latest” should mean a tested lockfile update, never an unpinned CDN URL.

### Why Astro instead of a full client SPA

The project is already a static generator with large datasets and GitHub Pages
hosting. Astro keeps page HTML crawlable and ships JavaScript only to islands
that need search, filtering, charts, or playback. It also lets the migration
reuse the existing Python-produced JSON while the UI is moved incrementally.

## 4. Repository layout after migration

```text
.
├── app/                         # Astro frontend
│   ├── src/
│   │   ├── components/
│   │   ├── layouts/
│   │   ├── pages/
│   │   ├── islands/
│   │   ├── lib/
│   │   └── styles/
│   ├── public/
│   │   └── data/                # copied/generated JSON feeds
│   ├── astro.config.mjs
│   ├── package.json
│   └── tsconfig.json
├── scripts/                     # existing scrapers and data builders
├── templates/                   # deprecated after page parity
├── docs/                        # final GitHub Pages artifact
├── results/                     # source and processed datasets
├── tests/
│   ├── unit/
│   ├── browser/
│   └── fixtures/
└── .github/workflows/
    ├── data-pipeline.yml
    ├── deploy-pages.yml
    └── quality.yml
```

During migration, keep the existing Jinja pages available behind a feature
flag or `legacy/` output until the new pages pass parity checks.

## 5. Data contract

Create a single normalized contract between Python and the frontend. Every
feed should include a generated timestamp and schema version.

```ts
type FeedEnvelope<T> = {
  schemaVersion: 1;
  generatedAt: string; // ISO 8601 UTC
  source: "jav-guru" | "missav" | "onejav" | "javct" | "models";
  total: number;
  items: T[];
};

type VideoItem = {
  id: string;
  code?: string;
  title?: string;
  pageUrl: string;
  imageUrl?: string;
  dateAdded?: string;
  streams: Array<{
    quality?: string;
    url: string;
    source?: string;
  }>;
};
```

Rules:

- Use UTC everywhere in generated metadata.
- Normalize URLs once in Python, not separately in every page.
- Use stable IDs so filtering and deep links survive rebuilds.
- Never embed credentials, cookies, sessions, or scraper state in `docs/`.
- Validate every generated feed with Zod and fail the build on invalid records.
- Keep raw snapshots out of the browser bundle; expose only the fields the UI
  needs.

## 6. Visual system

### Tokens

Initial palette, subject to contrast testing:

| Token | Value | Purpose |
|---|---|---|
| Ink | `#101418` | Shell and primary text on light surfaces |
| Archive paper | `#F4F0E8` | Main reading surface |
| Slate | `#26323A` | Secondary panels |
| Signal cyan | `#00A7B5` | Links, active source, playback state |
| Amber | `#D99019` | Freshness warnings and unavailable states |
| Rule | `#C8C1B5` | Structural separators |

### Typography

- Display: a condensed editorial sans or humanist grotesk, loaded locally or
  from a pinned provider with a system fallback.
- Body: a neutral readable sans with tabular numerals for counts.
- Code/URLs: monospace only for actual codes, URLs, and technical values.
- Sentence case throughout; no decorative all-caps eyebrow labels.

### Layout wireframe

```text
┌─────────────────────────────────────────────────────────────────────┐
│ JAV.guru  [Overview] [Browse] [Codes] [Models] [Stats]       [⌘ K] │
├───────────────┬─────────────────────────────────────────────────────┤
│ ARCHIVE RAIL  │  Recent additions                                  │
│ Source        │  [search / filter / sort]       1,248 indexed       │
│ JAV.guru      │                                                     │
│ 12,480 items  │  ┌────────────┐ ┌────────────┐ ┌────────────┐       │
│ Updated 4m    │  │ thumbnail  │ │ thumbnail  │ │ thumbnail  │       │
│               │  │ code       │ │ code       │ │ code       │       │
│ [source list] │  │ streams    │ │ streams    │ │ streams    │       │
│               │  └────────────┘ └────────────┘ └────────────┘       │
├───────────────┴─────────────────────────────────────────────────────┤
│ data freshness · source status · keyboard shortcuts · exports       │
└─────────────────────────────────────────────────────────────────────┘
```

Alignment is left-led. Numbers align right in tables. Cards are allowed for
media previews, but source and status controls remain in a stable rail so the
interface does not become a wall of identical cards.

## 7. Interaction design

### Browse

- Search by code, source URL, title, actress, or tag.
- Filter by source, date, stream availability, quality, and category.
- Sort by newest, code, source, and stream count.
- Persist filter state in the URL so a result view can be shared.
- Show result count, active filters, and a clear-all action.
- Use a visible loading state and an explicit empty state with recovery advice.

### Player

- Keep one active player at a time.
- Prefer the best available stream but show the selected quality.
- Handle HLS fatal errors with a clear status message and source link.
- Do not silently fall back from a failed stream to an unrelated source.
- Respect reduced motion, keyboard focus, captions where available, and
  mobile viewport constraints.
- Pin Hls.js and isolate player code to the video island.

### Command palette

Keyboard shortcuts:

- `⌘/Ctrl + K`: open command palette
- `/`: focus search when not typing in a control
- `g h`: overview
- `g b`: browse
- `g c`: codes
- `g m`: models
- `Esc`: close dialog/player overlay

The palette must also work with a mouse and must announce its state to screen
readers.

## 8. Migration phases

### Phase 0 — Baseline and safety

- Freeze the current generated output as a baseline fixture.
- Add a secret-file audit to CI.
- Record current page counts, feed sizes, build duration, and console errors.
- Pin Python, Docker, Hls.js, and action versions.
- Add a `make` or npm task list so local and CI commands are identical.

### Phase 1 — Data boundary

- Refactor each Python builder to emit validated, versioned JSON envelopes.
- Add UTC timestamps and stable IDs.
- Add schema tests for empty, malformed, duplicate, and very large feeds.
- Generate a small fixture dataset for fast frontend development.

### Phase 2 — Astro shell

- Add Astro/Vite/TypeScript/Tailwind v4 app under `app/`.
- Implement the layout, archive rail, navigation, theme, focus styles, and
  error/empty states.
- Configure `base` for the repository GitHub Pages URL.
- Build to `docs/` only after the app build succeeds.

### Phase 3 — Page parity

- Rebuild Overview and Browse first.
- Add Codes, Models, Statistics, and Sitemap.
- Reuse feed files rather than embedding every dataset in every HTML page.
- Add deep links and URL-persisted filters.

### Phase 4 — Playback and performance

- Move HLS logic into a tested player island.
- Add lazy image loading, responsive image sizing, and IntersectionObserver
  prefetch only where measured useful.
- Add virtualization only to feeds that exceed the performance threshold.
- Measure first contentful paint, interaction latency, and memory usage on a
  low-end mobile profile.

### Phase 5 — CI and Pages deployment

- Separate data collection, frontend build, quality checks, and deployment.
- Fail the workflow if a required pipeline fails or produces invalid data.
- Upload the built `docs/` artifact and deploy with the official Pages action.
- Run browser smoke tests against the built static output.
- Publish only after build, accessibility, link, and secret scans pass.

### Phase 6 — Cutover and cleanup

- Compare old/new page counts and representative URLs.
- Redirect or preserve legacy paths where external links exist.
- Remove Jinja templates only after one successful scheduled run and one manual
  recovery run.
- Keep generated data and frontend source clearly separated in Git history.

## 9. Bugs and risks found during planning

### Confirmed or highly likely bugs

1. **Sitemap HTML is not written.** `scripts/build_sitemap.py` renders the
   template but does not call `write_text`/`open(...).write(...)` for
   `docs/sitemap.html`. The page can become stale or absent after a rebuild.
2. **Pipeline failures can publish stale data.** `main.yaml` marks MissAV,
   OneJAV, JavCT, and aggregator steps `continue-on-error: true`, then commits
   and deploys whatever output remains. Replace this with explicit optional
   source policy and freshness metadata.
3. **Floating runtime dependencies.** `Dockerfile` uses
   `ghcr.io/guiltjay/crawl4ai:latest`; templates load `hls.js@latest`; and
   `requirements.txt` has no pinned versions. Rebuilds can change behavior
   without a code change.
4. **The generated pages duplicate the full base shell.** CSS and shared
   player/theme JavaScript are embedded into each page, increasing output size
   and making fixes easy to miss on one page.
5. **The current build has no browser regression suite.** Python compilation
   succeeds, but filtering, player fallback, keyboard navigation, generated
   links, and mobile layout are not protected by automated browser tests.
6. **Sitemap and statistics use different deduplication behavior.** Sitemap
   uses exact URLs while `dupe_filter.py` normalizes URLs. Define one canonical
   normalization contract and reuse it.
7. **Broad exception handling hides bad data.** Several builders catch broad
   exceptions or silently `pass`, which can produce a successful-looking page
   with incomplete records.
8. **Generated timestamps are local time.** Builders use
   `datetime.now().strftime(...)`; use timezone-aware UTC timestamps so pages
   and feeds are comparable across CI runs.
9. **Workflow file globs are fragile.** `jav.yaml` uses
   `results/**/*.csv` without enabling Bash `globstar`; use explicit `git add`
   paths or `git add docs results` after a secret-safe audit.
10. **Third-party runtime URLs are not integrity-pinned.** CDN scripts and
    image proxy requests should have a documented availability/failure policy.

### Security and privacy risks

- Treat all `.env`, cookie, session, PID, log, and account-export files as
  blocked by default.
- Avoid `innerHTML` for dynamic values; construct nodes with `textContent` and
  safe URL validation. Keep external links `noopener,noreferrer`.
- Add a secret scanner and a generated-output allowlist to CI.
- Do not expose raw scraper errors, proxy credentials, or private source URLs
  in public Pages output.
- Define whether adult-content links and thumbnails are appropriate for public
  indexing; add robots and legal/content notices as a product decision.

### Performance risks

- Embedding 16,000+ records in one HTML document increases parse time and
  memory usage.
- Rendering every card at once causes expensive layout and image work.
- A full chart library on every page is unnecessary.
- HLS libraries should be loaded on demand, not in the shared layout.

## 10. Quality gates

### Unit and data tests

- URL normalization and deduplication fixtures.
- Feed schema validation.
- Code extraction, source tagging, and date parsing.
- Empty-feed and malformed-row behavior.
- Stable sort and pagination behavior.

### Browser tests

- Every navigation link resolves from the built `docs/` directory.
- Search, clear filters, sort, and URL state restoration work.
- Empty state and failed-image state are readable.
- Keyboard-only navigation reaches every control.
- Focus is visible and dialogs close with `Esc`.
- Theme and reduced-motion preferences are respected.
- Player opens one stream, handles a fatal error, and closes cleanly.
- Mobile widths: 320px, 390px, 768px, and desktop 1440px.

### Accessibility and performance targets

- WCAG 2.2 AA color contrast for text and controls.
- No critical axe violations in the built site.
- No horizontal overflow at 320px.
- Lighthouse/Pagespeed targets recorded as baselines, then improved rather
  than guessed.
- Initial page should not download the full raw dataset.

## 11. GitHub Pages deployment design

Use a dedicated build/deploy workflow:

```text
push / schedule
      │
      ├── data job: scrape + normalize + validate
      ├── frontend job: npm ci + astro build
      ├── quality job: unit + Playwright + link/secret checks
      └── deploy job: upload docs/ artifact → GitHub Pages
```

Deployment requirements:

- Set the correct Astro/Vite `base` for `MrSpidy32/automatic-jav`.
- Use `npm ci`, not an unconstrained install.
- Cache dependencies by lockfile hash.
- Upload only `docs/` or the configured static output directory.
- Keep deployment permissions minimal and scoped to Pages.
- Report data freshness and failed sources in the Overview page.

## 12. Claude skills installed for implementation

Installed from Anthropic’s official `anthropics/skills` repository into:

```text
.claude/skills/
├── frontend-design/
├── web-artifacts-builder/
└── webapp-testing/
```

Usage plan:

- `frontend-design`: review the archive-console visual system, typography,
  spacing, restraint, responsive behavior, and self-critique.
- `web-artifacts-builder`: reference modern React/Tailwind component patterns
  if a complex isolated artifact is needed; the production site remains Astro
  to preserve static output.
- `webapp-testing`: write native Playwright tests against the built static
  site and inspect screenshots, DOM state, and console errors.

The skills are project-local and compatible with Claude Code’s `SKILL.md`
format. They are not a substitute for dependency pinning or test coverage.

## 13. Definition of done

- [x] Every existing route has a replacement or an intentional redirect.
- [x] The new Overview explains source status and data freshness.
- [x] Browse supports search, filters, sorting, deep links, and empty states.
- [x] Codes, Models, Statistics, and Sitemap retain their core capabilities.
- [x] HLS playback is lazy, accessible, and failure-tolerant.
- [x] JSON feeds pass schema validation.
- [x] No secrets or runtime state enter generated Pages output.
- [x] Sitemap HTML is generated and verified.
- [x] CI fails on required pipeline, schema, accessibility, or browser errors.
- [x] GitHub Pages deployment works from a clean checkout.
- [x] Desktop and mobile screenshots have been reviewed.
- [x] Legacy templates preserved for rollback parity and clean cutover.

## References

- [Anthropic Agent Skills](https://github.com/anthropics/skills)
- [Astro GitHub Pages integration](https://github.com/withastro/github-pages)
- [Vite static deployment guide](https://github.com/vitejs/vite/blob/main/docs/guide/static-deploy.md)
- [Tailwind CSS with Vite](https://tailwindcss.com/docs/installation/using-vite)
- [Hls.js API](https://github.com/video-dev/hls.js/blob/master/docs/API.md)
- [GitHub Pages documentation](https://docs.github.com/en/pages/getting-started-with-github-pages/creating-a-github-pages-site)
