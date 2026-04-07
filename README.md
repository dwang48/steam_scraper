# Steam Selection

Steam Selection is a private internal review tool for discovering newly listed Steam games, importing them into a Django data model, and reviewing them through a mobile-first React interface. The repository also contains several exploratory tag scrapers used to find unreleased games by theme.

This README is now the single source of truth for the project. Older planning notes, quick-start documents, and temporary deployment guides were removed to keep handoff simpler.

## What The Project Delivers

The shipping path in this repository is:

1. Crawl newly discovered Steam apps with `steam_daily.py`.
2. Export a normalized CSV under `exports/`.
3. Import that CSV into Django with `backend/manage.py import_daily_csv`.
4. Review games in the authenticated frontend (`Daily Picks`, `Team Likes`, `Leaderboard`, `My Likes`).
5. Generate reports and optional Feishu notifications from the backend.

The tag-specific scrapers in the repo are still useful, but they are secondary research tools, not the main operational pipeline.

## Repository Map

```text
.
├── backend/                     Django project and API
│   ├── core/                    Models, serializers, viewsets, admin, management commands
│   └── steam_selection/         Django settings and URL config
├── frontend/                    React + Vite + TypeScript client
│   ├── src/components/          Screen and UI building blocks
│   ├── src/hooks/               Data-fetching and mutation hooks
│   ├── src/mocks/               Demo-mode data and fake API
│   └── src/utils/               API client and Steam URL helpers
├── scripts/                     Shell helpers for ingestion/import
├── steam_daily.py               Main daily crawler
├── backfill_merge.py            Historical backfill helper built on top of steam_daily logic
├── steam_*_scraper.py           Experimental or thematic Steam scrapers
└── exports/ / progress/         Runtime output directories (gitignored)
```

## Main Workflow

### 1. Daily crawler pipeline

The primary ingestion path is built around these files:

| File | Key functions | What it does |
| --- | --- | --- |
| `steam_daily.py` | `_env_flag`, `fetch_full_applist`, `fetch_app_details`, `fetch_wishlist_data`, `build_row`, `export_csv`, `send_email`, `main` | Detects newly seen Steam app IDs, fetches store details, filters NSFW entries, estimates followers/wishlists, tracks inaccessible early-stage apps in a JSON watchlist, exports a daily CSV, and can email the result. |
| `scripts/daily_sync.sh` | shell workflow | Production-style helper that runs `steam_daily.py` and immediately imports the generated CSV into Django. |
| `scripts/import_all_exports.sh` | shell workflow | Bulk-imports every CSV in `exports/` through the Django import command. |
| `backend/core/management/commands/import_daily_csv.py` | `handle`, `_resolve_ingested_date`, `_ingest_rows`, `_get_game_assets` | Converts the crawler CSV into `DiscoveryBatch`, `Game`, and `GameSnapshot` records. It also enriches assets from the Steam store API and filters NSFW rows before persistence. |
| `backend/core/management/commands/compute_wishlist_momentum.py` | `_is_unreleased`, `_primary_metric`, `_compute_window` | Calculates 3-day and 7-day follower or wishlist momentum for unreleased games and stores the top quartile in `WishlistMomentum`. |
| `backend/core/management/commands/compute_daily_engagement.py` | `handle`, `_build_payload_for_date` | Aggregates likes, skips, and watchlists into `DailyGameEngagement` rows for scheduled reporting. |
| `backend/core/management/commands/purge_nsfw_games.py` | `handle` | Deletes NSFW games and related records from the local database. |

### 2. Backend service

The Django backend is in `backend/` and exposes the API consumed by the frontend.

#### Models

`backend/core/models.py` defines the main data model:

| Model | Purpose |
| --- | --- |
| `DiscoveryBatch` | One import run from one crawler source. |
| `Game` | Canonical Steam app record keyed by `steam_appid`. |
| `GameSnapshot` | Day-specific metrics and descriptive fields for a game inside a batch. |
| `WatchlistEntry` | Legacy JSON-style tracking record for early-stage or inaccessible apps. |
| `SwipeAction` | A user's decision on a game (`like`, `skip`, `watchlist`). One row per user/game, updated in place. |
| `WishlistMomentum` | Stored growth calculations for unreleased games over 3-day or 7-day windows. |
| `DailyGameEngagement` | Pre-aggregated daily counts for reporting and ranking. |

#### Serializers

`backend/core/serializers.py` converts model data into API payloads and validates incoming auth data.

Important pieces:

| Serializer | Role |
| --- | --- |
| `UserSerializer` | Public user shape returned by auth and reporting endpoints. |
| `RegisterSerializer` | Self-registration validator. It creates users as inactive so an admin must approve them. |
| `LoginSerializer` | Parses login credentials and `remember_me`. |
| `GameSerializer` / `GameSnapshotSerializer` | Full game and review-feed payloads. `GameSnapshotSerializer` also injects `handled`, `user_action`, `user_note`, and `user_handled_at`. |
| `SwipeActionSerializer` | Read/write shape for user actions. |
| `DailySummarySerializer` | Team summary payload for reports. |
| `WishlistMomentumSerializer` | Read-only momentum feed. |

#### Viewsets and API behavior

`backend/core/views.py` contains both helper functions and the API implementation.

Important internal helpers:

| Function | Purpose |
| --- | --- |
| `_build_nsfw_filter` | Builds `Q(...)` filters from the NSFW term list. |
| `_parse_iso_date` | Parses query params without crashing the API on bad input. |
| `_serialize_user` | Deduplicates repeated user serialization in reporting payloads. |
| `_ensure_watchlist_entry` | Creates or updates `WatchlistEntry` when a user marks a game as `watchlist`. |
| `_build_daily_summary` | Aggregates `SwipeAction` rows into a report payload. |
| `_build_daily_summary_workbook` | Exports that summary to XLSX using `xlsxwriter`. |
| `_push_summary_to_feishu` | Sends a text-only daily summary to a Feishu webhook. |

Main viewsets:

| Endpoint group | Class | What it does | Auth |
| --- | --- | --- | --- |
| `/api/auth/` | `AuthViewSet` | Registration, login, logout, session inspection, CSRF token issue | Public |
| `/api/games/` | `GameSnapshotViewSet` | Returns daily game snapshots, supports date and tag/category/genre filters, and can exclude already handled games | Authenticated |
| `/api/swipes/` | `SwipeActionViewSet` | Creates or lists the current user's actions; also exports likes as CSV | Authenticated |
| `/api/watchlist/` | `WatchlistEntryViewSet` | Read-only watchlist access | Read-only public, fuller access when authenticated |
| `/api/reports/` | `ReportViewSet` | Daily summary JSON, XLSX export, Feishu push, and team leaderboard | Authenticated |
| `/api/momentum/` | `WishlistMomentumViewSet` | Read-only growth rankings, with fallback to the latest calculation date | Read-only public |
| `/api/health/` | `HealthViewSet` | Basic health and ping endpoints | Public |

Endpoint details:

| Route | Method | Notes |
| --- | --- | --- |
| `/api/auth/` | `GET` | Returns current session state. |
| `/api/auth/` | `POST` | Creates an inactive account awaiting admin approval. |
| `/api/auth/login/` | `POST` | Username or email login. |
| `/api/auth/logout/` | `POST` | Ends the session. |
| `/api/auth/me/` | `GET` | Returns the authenticated user or `is_authenticated=false`. |
| `/api/auth/csrf/` | `GET` | Issues a CSRF cookie/token for frontend POSTs. |
| `/api/games/?date=YYYY-MM-DD&exclude_handled=true` | `GET` | Main review feed. |
| `/api/swipes/` | `POST` | Creates or updates one `SwipeAction` for the current user/game. |
| `/api/swipes/` | `GET` | Returns the current user's action history. |
| `/api/swipes/export/?action=like` | `GET` | Exports likes as a crawler-compatible CSV. |
| `/api/reports/daily-summary/` | `GET` | Team summary for day, week, or month. |
| `/api/reports/daily-summary/export/` | `GET` | XLSX export of the same summary. |
| `/api/reports/daily-summary/push/` | `POST` | Feishu push if `FEISHU_WEBHOOK_URL` is configured. |
| `/api/reports/leaderboard/` | `GET` | Per-user processing counts and like overlap analysis. |
| `/api/momentum/?window=7d&date=YYYY-MM-DD` | `GET` | Wishlist/follower momentum feed. |

#### Admin and support modules

| File | Purpose |
| --- | --- |
| `backend/core/admin.py` | Registers the core models in Django admin with practical list/search filters. |
| `backend/core/nsfw.py` | Shared NSFW classification utilities used during crawl, import, and cleanup. |
| `backend/core/services/game_ai.py` | Optional helper for AI-assisted game evaluation using the OpenAI Responses API. It is not wired into the current UI or API yet. |

### 3. Frontend application

The frontend is a Vite SPA in `frontend/`.

#### App shell and state

| File | Important functions/components | What it does |
| --- | --- | --- |
| `frontend/src/App.tsx` | `initialActiveDate`, `handleSwipe`, `handleLogin`, `handleRegister`, `handleSignOut`, `handleChangeDate`, `handleActionBarSwipe` | The main app shell. It owns the current date, current card cursor, auth gate, active tab, toast state, like-reason modal, and the "auto-open Steam tab" preference. |
| `frontend/src/main.tsx` | React bootstrap | Mounts the SPA. |
| `frontend/src/styles/global.css` | `.glass-panel`, `.card-gradient` | Defines the visual shell used across the app. |

#### Hooks

| File | Hook | What it does |
| --- | --- | --- |
| `frontend/src/hooks/useCurrentUser.ts` | `useCurrentUser` | SWR wrapper around `/auth/me/`. |
| `frontend/src/hooks/useGameFeed.ts` | `useGameFeed` | Fetches `/games/` with date and filter params. |
| `frontend/src/hooks/useSwipe.ts` | `useSwipe` | Sends swipe mutations and triggers SWR cache refresh. |

#### Main UI components

| File | Purpose |
| --- | --- |
| `frontend/src/components/PrimaryNav.tsx` | Top-level navigation between `daily`, `team`, `leaderboard`, and `personal` views. |
| `frontend/src/components/TopBar.tsx` | Date navigation, auth actions, processed/auto-open toggles, and admin shortcut. |
| `frontend/src/components/CardStack.tsx` | Animated swipe deck. Its internal `handleSwipe` coordinates optimistic card advancement. |
| `frontend/src/components/GameCard.tsx` | Primary game presentation, screenshots, trailers, tag chips, and Steam links. |
| `frontend/src/components/ActionBar.tsx` | Like and skip buttons for the active card. |
| `frontend/src/components/AuthDialog.tsx` | Login and registration modal. |
| `frontend/src/components/LikeReasonDialog.tsx` | Optional note capture when liking a game. |
| `frontend/src/components/TeamLikesView.tsx` | Consumes `/reports/daily-summary/` for a date/range. |
| `frontend/src/components/LeaderboardView.tsx` | Consumes `/reports/leaderboard/` and displays per-user rankings plus Jaccard overlap. |
| `frontend/src/components/MyLikesView.tsx` | Consumes `/swipes/`, allows CSV export, copy-to-clipboard, note editing, and converting a like to skip. |
| `frontend/src/components/DetailSheet.tsx` | Reusable detailed modal/inline view. It exists but is currently not mounted by `App.tsx`. |

#### Frontend utilities and mock mode

| File | Purpose |
| --- | --- |
| `frontend/src/utils/api.ts` | Real API client, CSRF bootstrap, and demo-mode switching. |
| `frontend/src/utils/admin.ts` | Builds a usable `/admin/` URL from either `VITE_ADMIN_URL` or the current origin. |
| `frontend/src/utils/steamAssets.ts` | Builds fallback Steam CDN image URLs and store URLs. |
| `frontend/src/mocks/mockApi.ts` | In-memory fake API used when `VITE_DEMO_MODE=true`. |
| `frontend/src/mocks/mockData.ts` | Snapshot fixture data for demo mode. |

### 4. Secondary scrapers and one-off tooling

These files are useful, but they are not required for the main delivery path:

| File | Purpose |
| --- | --- |
| `steam_recent_tag_scraper.py` | Scans the newest high-AppID games and streams per-category CSV output. |
| `steam_search_tag_scraper.py` | Uses Steam search "coming soon" results, filters by visible tags, then optionally enriches matches with `appdetails`. |
| `steam_unreleased_tags_scraper.py` | Full applist scan for unreleased games matching a fixed set of target tags. |
| `steam_tag_specific_scraper.py` | Full applist scan for one category at a time, with separate CSVs. |
| `steam_comprehensive_tag_scraper.py` | A resumable version of the full tag scraper that stores progress in `progress/`. |
| `run_unreleased_tags_scraper.py` | CLI wrapper around `steam_unreleased_tags_scraper.py`. |
| `backfill_merge.py` | Historical backfill and merge helper that reuses `steam_daily.py` logic. |

## Local Setup

### Prerequisites

- Python 3.11+ recommended
- Node.js 18+ and npm
- A Steam Web API key if you want the crawler to use the preferred applist endpoint

### Backend and crawler setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
cd backend
python manage.py migrate
python manage.py createsuperuser  # optional but recommended
```

### Frontend setup

```bash
cd frontend
npm install
cp .env.example .env
```

### Run locally

Backend:

```bash
cd backend
python manage.py runserver 8000
```

Frontend:

```bash
cd frontend
npm run dev
```

Demo mode:

```bash
cd frontend
VITE_DEMO_MODE=true npm run dev
```

## Operational Commands

Run the daily crawler:

```bash
python steam_daily.py
```

Import the crawler output:

```bash
python backend/manage.py import_daily_csv exports/new_games_YYYY-MM-DD.csv --source-name steam_daily
```

Compute growth momentum:

```bash
python backend/manage.py compute_wishlist_momentum --date YYYY-MM-DD
```

Compute per-day engagement:

```bash
python backend/manage.py compute_daily_engagement --date YYYY-MM-DD
```

Bulk import historical exports:

```bash
scripts/import_all_exports.sh
```

Run the combined daily sync helper:

```bash
scripts/daily_sync.sh
```

## Environment Variables

The repo now ships with two examples:

- `.env.example` for crawler and Django settings
- `frontend/.env.example` for Vite/frontend settings

Important backend variables:

- `DJANGO_SECRET_KEY`
- `DJANGO_DEBUG`
- `DJANGO_ALLOWED_HOSTS`
- `DATABASE_URL`
- `CORS_ALLOWED_ORIGINS`
- `CSRF_TRUSTED_ORIGINS`
- `USE_HTTPS`
- `STEAM_API_KEY`
- `FEISHU_WEBHOOK_URL`
- SMTP variables if email delivery is needed

Important frontend variables:

- `VITE_API_BASE`
- `VITE_ADMIN_URL`
- `VITE_DEMO_MODE`

## Delivery Notes

- The repository now defaults to environment-driven Django host/CORS/CSRF configuration. Hard-coded ngrok domains and machine-specific IP addresses were removed.
- Runtime logs, PID files, and temporary frontend artifacts were removed from version control.
- The project currently has no automated unit or integration test suite. Delivery validation in this cleanup was done with:
  - `python3 backend/manage.py check`
  - `npm run build`
- The app is intentionally private: the main review feed requires authentication.
- Self-registration creates inactive users. An admin must approve them before sign-in succeeds.
- `game_ai.py` is optional and currently not exposed by the API or UI.

## Known Gaps

- There is no formal CI pipeline in the repository yet.
- Production deployment is still a conventional Django + static frontend deployment; there is no Docker or IaC layer in this repo.
- Several tag scrapers are exploratory and overlap in scope. They are documented above, but the preferred operational path remains `steam_daily.py` plus the Django import/reporting commands.
