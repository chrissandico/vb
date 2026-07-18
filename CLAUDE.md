# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A single-page Streamlit app ("Daily Activities") that gives Preston or Isaac a randomized daily list of tasks, a workout, and a bonus challenge, pulled live from a Google Sheet.

## Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run the app locally
streamlit run app.py

# Regenerate bcrypt password hashes (requires `pip install bcrypt` — not in requirements.txt)
python hash.py
```

There is no test suite, linter, or build step in this repo.

## Architecture

Everything lives in `app.py`. There is no backend service — it talks directly to Google Sheets via `gspread`.

- `get_sheets_client()` — builds an authenticated `gspread` client. It checks `st.secrets['gcp_service_account']` first (Streamlit Cloud deployment), then falls back to a local `service-account.json` file (local dev). Cached with `@st.cache_resource`.
- `fetch_activities(name)` — opens the spreadsheet (`SPREADSHEET_ID` constant) and reads two worksheets: `poppies` (tasks) and `exercises` (workouts). It randomly samples 5 tasks, 5 exercises, and one extra "bonus" task not already selected, then reshapes rows into the dict structure the UI renders. `name` is accepted but not currently used to filter/personalize the sheet query — it's only used for the UI header.
- `extract_youtube_id(url)` — pulls a video ID out of `youtu.be/...`, `youtube.com/watch?v=...`, or `youtube.com/embed/...` URLs so `st.video()` can embed it.
- `main()` — Streamlit UI: name radio button (Preston/Isaac), a submit button, then three rendered sections (tasks, workout with embedded YouTube videos, bonus challenge) using custom HTML/CSS cards.

### Expected Google Sheet structure

- **poppies**: `Task Name`, `Task Description`, `Type`, `Duration`
- **exercises**: `Exercise`, `Sets`, `Instructions`, `Example` (a YouTube URL), `Type`
- **history**: historical activity log (not currently read by `app.py`)

### Credentials

- `service-account.json` (local) / `st.secrets["gcp_service_account"]` (Streamlit Cloud) — Google service account for Sheets API access. Never commit `service-account.json`; it's gitignored. `.streamlit/secrets.toml.example` shows the expected secrets format for cloud deployment.
- `credentials.yaml` and `hash.py` (bcrypt) are leftover scaffolding from an earlier login-screen attempt (see git history: "added login screen" → "Reverted back with no login screen"). **`app.py` currently has no authentication** — anyone with the URL can use the app. Don't assume `credentials.yaml` is wired up without checking `app.py` first.

### Workout plan generator

`workout_generator.py` and the `.claude/skills/workout-plan/` project skill
generate a 6-exercise, 30-minute workout plan filtered by `Type` (from the
`exercises` worksheet) and email it to theprofmeta@gmail.com via Gmail SMTP.

```bash
python workout_generator.py --type "Core"           # generates and emails
python workout_generator.py --type "Core" --dry-run # prints instead of emailing
```

Requires a `[gmail]` section in `.streamlit/secrets.toml` with `sender_email`
and `app_password` (a Gmail App Password, not the real account password) —
see `.streamlit/secrets.toml.example`. Shares Google Sheets credential
loading with `app.py` via `sheets_client.py`.

### `.kiro/steering/` docs

These describe an earlier architecture (AWS Lambda backend, bcrypt login flow) that no longer matches `app.py`, which now talks to Google Sheets directly with no login. Treat `.kiro/steering/*` as historical context, not ground truth — verify against `app.py` before relying on it.
