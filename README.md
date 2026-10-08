# Wilmington Area Jobs Dashboard

A GitHub Pages dashboard for job openings in the Wilmington, NC region.

**Region:** Brunswick, New Hanover, and Pender counties.

## Important source rule

This project **does not scrape Indeed or LinkedIn**.

The initial architecture is designed for:
- NCWorks
- local government career portals
- school systems
- colleges/universities
- employer career pages
- permitted public job feeds/APIs

## Architecture

```text
Public job sources
       |
       v
collector/collect.py
       |
       v
data/jobs.json
       |
       v
docs/index.html
       |
       v
GitHub Pages
```

GitHub Actions runs the collector on a schedule and commits updated `data/jobs.json`.

## Run locally

```bash
python collector/collect.py
```

Then open `docs/index.html`.

## Enable GitHub Pages

1. Create a GitHub repository.
2. Upload this project.
3. Go to **Settings → Pages**.
4. Choose **Deploy from a branch**.
5. Select `main` and `/docs`.
6. Save.

The scheduled workflow will run daily.

## Adding a source

Edit `collector/sources.json`.

Each source has:
- `name`
- `county`
- `url`
- `type`
- optional `adapter`

The collector currently supports:
- JSON feeds
- RSS feeds
- HTML pages with JSON-LD JobPosting data
- a configurable generic HTML adapter

The generic adapter is intentionally conservative. For important employers, create a dedicated adapter rather than relying on fragile CSS selectors.

## Roadmap

### Phase 1
- working GitHub Pages dashboard
- source configuration
- daily GitHub Action
- duplicate detection
- filters
- salary display
- new-job highlighting

### Phase 2
- dedicated adapters for NCWorks and major local employer systems
- employer career pages
- closing-date detection
- better salary extraction
- county/geographic validation

### Phase 3
- historical job database
- weekly hiring trends
- industry trends
- employer hiring activity
- Leland vs. Wilmington vs. Brunswick/Pender comparisons
