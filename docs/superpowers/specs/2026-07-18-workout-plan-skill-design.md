# Workout Plan Skill — Design

**Date:** 2026-07-18
**Status:** Approved

## Purpose

Generate a 6-exercise, 30-minute workout plan filtered by a requested "type" (e.g. "Upper Body", "Core"), pulled from the existing `exercises` Google Sheet, and email it to theprofmeta@gmail.com. Usable both as a standalone script and as a Claude Code project skill.

## Architecture

Two new pieces, kept separate so the logic works whether Claude Code is running or not:

1. **`workout_generator.py`** (new, root-level script) — does the real work: reads the `exercises` sheet, picks exercises, composes and sends the email. Runnable standalone: `python workout_generator.py --type "Upper Body"`.
2. **`.claude/skills/workout-plan/SKILL.md`** (new project skill) — thin wrapper. When invoked in Claude Code (e.g. "give me a 30-min core workout"), it shells out to `workout_generator.py --type "<type>"` and reports the result back.

`sheets_client.py` (new, shared module) — extracts the credential-loading logic currently inline in `app.py`'s `get_sheets_client()`, since `workout_generator.py` needs the same Google Sheets auth but can't rely on Streamlit's `st.secrets` / `st.cache_resource` outside a running Streamlit app. `app.py` keeps its own Streamlit-flavored wrapper (caching, `st.error`) around the shared function — no behavior change to the existing app.

## Data flow

1. Load all rows from the `exercises` worksheet via `sheets_client`.
2. Split each row's `Type` field on commas (`"Core, Mobility"` → `["Core", "Mobility"]`) so multi-type exercises are supported, even though today's rows are all single-type.
3. Case-insensitive match: keep rows where the requested type is in that exercise's type list.
4. If ≥6 rows match: randomly pick 6, no repeats.
5. If 1–5 rows match: use all of them, then randomly repeat some (shuffled, not the same one back-to-back) to fill out 6 total. Repeats are labeled "(Round 2)" in the email.
6. If 0 rows match: stop with a clear error, no email sent.
7. Assign 5 minutes per exercise (30 ÷ 6, even split). Build an HTML email: numbered list, each entry showing exercise name, sets, instructions, minutes, and a "Watch demo" link to the YouTube URL. Send via Gmail SMTP (SSL, port 465).

## Config / secrets

Add a `[gmail]` table to `.streamlit/secrets.toml` (already gitignored):

```toml
[gmail]
sender_email = "theprofmeta@gmail.com"
app_password = "xxxx xxxx xxxx xxxx"  # Gmail App Password, not the real account password
```

`workout_generator.py` reads this file directly with the `toml` package (new `requirements.txt` entry) rather than through `st.secrets`, so it works outside Streamlit. `.streamlit/secrets.toml.example` is updated to document the new section. Recipient is hardcoded to theprofmeta@gmail.com (same account sends and receives) — not a CLI flag, since there's only one recipient today.

## Error handling

- Sheets auth failure, 0 matching exercises, or SMTP send failure → the script prints a clear message to stderr and exits non-zero. No partial or misleading "success" output. The Claude Code skill surfaces that message back to the user rather than claiming success.

## Testing

- `--dry-run` flag prints the composed email to the console instead of sending, so formatting can be checked without spamming the inbox.
- Manual test: run with a real type (e.g. "Core") and confirm the email arrives with 6 exercises and working video links.

## Out of scope

- Editing existing sheet rows to add multi-type values — the parser supports it, but no existing data is being changed.
- Per-exercise duration data / a `Duration` column on the `exercises` sheet — even 5-minute split only, for now.
- Any UI changes to the existing Streamlit app.
