# Workout Plan Skill Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a standalone script that generates a 6-exercise, 30-minute workout plan filtered by type from the existing `exercises` Google Sheet and emails it, plus a thin Claude Code project skill that wraps it.

**Architecture:** A new shared `sheets_client.py` module extracts Google Sheets credential-loading out of `app.py` so it can be reused without Streamlit. A new `workout_generator.py` CLI script uses it to fetch exercises, pick 6 matching the requested type (repeating to fill gaps if fewer than 6 match), and emails an HTML summary via Gmail SMTP. A new `.claude/skills/workout-plan/SKILL.md` invokes that script from Claude Code.

**Tech Stack:** Python, gspread, oauth2client, toml (new dependency), smtplib/email (stdlib), argparse (stdlib).

## Global Constraints

- Spreadsheet ID is `1CSokDhyaVLpc9tJgJDKD-y6G_ClmN7aRFrUL6xursro` (same as `app.py`).
- Read from the `exercises` worksheet only (columns: `Exercise`, `Sets`, `Instructions`, `Example`, `Type`).
- Exactly 6 exercises per plan, 30 minutes total (5 minutes each, even split).
- `Type` field may contain multiple comma-separated values (e.g. `"Core, Mobility"`); match case-insensitively against any of them.
- If ≥6 exercises match the requested type: pick 6 at random, no repeats.
- If 1–5 match: use all of them, then repeat randomly-chosen ones (shuffled) to fill to 6; each repeat is labeled "(Round 2)" in the email.
- If 0 match: exit non-zero with a clear error, no email sent.
- Recipient and sender are both `theprofmeta@gmail.com`; credentials come from a `[gmail]` table in `.streamlit/secrets.toml` (`sender_email`, `app_password`), read directly with `toml`, not `st.secrets`.
- No existing behavior of `app.py`'s Streamlit UI may change.
- No automated test framework exists in this repo today (no pytest, no test files) — verification steps in this plan use manual smoke-test commands against the real Google Sheet (`service-account.json` is already present locally) instead of a new test suite, matching the approved spec's "Testing" section (`docs/superpowers/specs/2026-07-18-workout-plan-skill-design.md`).

---

### Task 1: Shared Sheets credential module + refactor `app.py`

**Files:**
- Create: `sheets_client.py`
- Modify: `app.py:1-29` (replace `get_sheets_client`'s body, keep the `@st.cache_resource` wrapper)

**Interfaces:**
- Produces: `sheets_client.get_client(secrets=None) -> gspread.Client | None` — `secrets` is any dict-like object that may contain a `gcp_service_account` key (e.g. `st.secrets`, or a plain `dict` from `toml.load()`). Returns `None` if no credentials are found anywhere (neither `secrets['gcp_service_account']` nor a local `service-account.json`).

- [ ] **Step 1: Write `sheets_client.py`**

```python
import os

import gspread
from oauth2client.service_account import ServiceAccountCredentials

SCOPE = [
    'https://spreadsheets.google.com/feeds',
    'https://www.googleapis.com/auth/drive',
]


def load_credentials(secrets=None):
    """Build ServiceAccountCredentials from a secrets dict (must contain
    'gcp_service_account') or fall back to a local service-account.json file.
    Returns None if neither source is available."""
    if secrets and 'gcp_service_account' in secrets:
        return ServiceAccountCredentials.from_json_keyfile_dict(
            secrets['gcp_service_account'], SCOPE)
    if os.path.exists('service-account.json'):
        return ServiceAccountCredentials.from_json_keyfile_name(
            'service-account.json', SCOPE)
    return None


def get_client(secrets=None):
    """Return an authorized gspread Client, or None if no credentials found."""
    creds = load_credentials(secrets)
    if not creds:
        return None
    return gspread.authorize(creds)
```

- [ ] **Step 2: Verify it fails before the refactor is wired up**

Run: `python -c "from sheets_client import get_client; c = get_client(); print('OK' if c else 'FAIL: no client')"`
Expected: `OK` (this confirms `service-account.json` in the repo root is picked up correctly — if it prints `FAIL`, stop and check that `service-account.json` exists in the current directory before continuing)

- [ ] **Step 3: Refactor `app.py` to use the shared module**

Replace lines 1-29 of `app.py` (the imports through the end of `get_sheets_client`) with:

```python
import streamlit as st
import gspread
import random
import json
import os

from sheets_client import get_client

# Google Sheets configuration
SPREADSHEET_ID = "1CSokDhyaVLpc9tJgJDKD-y6G_ClmN7aRFrUL6xursro"

@st.cache_resource
def get_sheets_client():
    """Initialize and cache the Google Sheets client"""
    secrets = st.secrets if hasattr(st, 'secrets') else None
    client = get_client(secrets)
    if not client:
        st.error("Google Sheets credentials not found. Please configure secrets.")
    return client
```

(This drops the now-unused `from oauth2client.service_account import ServiceAccountCredentials` import and the inline `scope` list — both moved into `sheets_client.py`.)

- [ ] **Step 4: Verify the Streamlit app still starts cleanly**

Run: `python -c "import ast; ast.parse(open('app.py').read())"`
Expected: no output (confirms `app.py` is still syntactically valid after the edit)

Run: `python -c "import app"`
Expected: no output/errors (confirms all imports resolve and module-level code runs without raising)

- [ ] **Step 5: Commit**

```bash
git add sheets_client.py app.py
git commit -m "Extract shared Google Sheets credential loading into sheets_client.py"
```

---

### Task 2: Exercise selection logic

**Files:**
- Create: `workout_generator.py` (started here, extended in later tasks)

**Interfaces:**
- Consumes: nothing from Task 1 yet (wired in Task 4)
- Produces:
  - `parse_types(type_field: str) -> list[str]`
  - `select_exercises(all_records: list[dict], workout_type: str) -> list[dict]` — raises `ValueError` if no exercises match `workout_type`. Each returned dict is a shallow copy of the matched sheet row; repeated entries (used to fill gaps when fewer than 6 rows match) additionally have `'_repeat': True`.
  - Constants: `NUM_EXERCISES = 6`, `TOTAL_MINUTES = 30`, `MINUTES_PER_EXERCISE = TOTAL_MINUTES // NUM_EXERCISES`

- [ ] **Step 1: Write `workout_generator.py` with the selection logic**

```python
"""Generate a 30-minute, 6-exercise workout plan by type and email it."""
import random

NUM_EXERCISES = 6
TOTAL_MINUTES = 30
MINUTES_PER_EXERCISE = TOTAL_MINUTES // NUM_EXERCISES


def parse_types(type_field):
    """Split a Type column value like 'Core, Mobility' into ['Core', 'Mobility']."""
    if not type_field:
        return []
    return [t.strip() for t in str(type_field).split(',') if t.strip()]


def select_exercises(all_records, workout_type):
    """Pick NUM_EXERCISES exercises matching workout_type (case-insensitive).

    If fewer than NUM_EXERCISES rows match, randomly repeats matched rows
    (marked with '_repeat': True) to fill the remainder. Raises ValueError
    if zero rows match.
    """
    wanted = workout_type.strip().lower()
    matches = [
        r for r in all_records
        if wanted in [t.lower() for t in parse_types(r.get('Type', ''))]
    ]

    if not matches:
        raise ValueError(f"No exercises found with type '{workout_type}'.")

    if len(matches) >= NUM_EXERCISES:
        return random.sample(matches, NUM_EXERCISES)

    selected = list(matches)
    pool = list(matches)
    random.shuffle(pool)
    i = 0
    while len(selected) < NUM_EXERCISES:
        repeat = dict(pool[i % len(pool)])
        repeat['_repeat'] = True
        selected.append(repeat)
        i += 1
    random.shuffle(selected)
    return selected
```

- [ ] **Step 2: Verify with a quick smoke test against known fixture data**

Run:
```bash
python -c "
from workout_generator import select_exercises, parse_types

assert parse_types('Core, Mobility') == ['Core', 'Mobility']
assert parse_types('Core') == ['Core']
assert parse_types('') == []

# Simulate 2 matching rows -> must repeat to fill 6, all repeats marked
rows = [
    {'Exercise': 'A', 'Type': 'Core'},
    {'Exercise': 'B', 'Type': 'Core, Mobility'},
    {'Exercise': 'C', 'Type': 'Lower Body'},
]
result = select_exercises(rows, 'core')
assert len(result) == 6, result
assert all(r['Exercise'] in ('A', 'B') for r in result), result
assert sum(1 for r in result if r.get('_repeat')) == 4, result

# Simulate 0 matching rows -> raises
try:
    select_exercises(rows, 'Cardio')
    print('FAIL: expected ValueError')
except ValueError:
    pass

print('OK')
"
```
Expected: `OK`

- [ ] **Step 3: Verify against the real sheet data (exact-match and repeat-fill paths)**

Run:
```bash
python -c "
from sheets_client import get_client
from workout_generator import select_exercises

client = get_client()
sheet = client.open_by_key('1CSokDhyaVLpc9tJgJDKD-y6G_ClmN7aRFrUL6xursro')
rows = sheet.worksheet('exercises').get_all_records()

# 'Lower Body' has 6 matches in the sheet today -> no repeats
lb = select_exercises(rows, 'Lower Body')
assert len(lb) == 6
assert not any(r.get('_repeat') for r in lb), lb

# 'Upper Body' has 1 match today -> 5 repeats
ub = select_exercises(rows, 'Upper Body')
assert len(ub) == 6
assert sum(1 for r in ub if r.get('_repeat')) == 5, ub

print('OK')
"
```
Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add workout_generator.py
git commit -m "Add exercise selection logic for workout plan generator"
```

---

### Task 3: Email composition, secrets, and sending

**Files:**
- Modify: `workout_generator.py` (append to the file created in Task 2)
- Modify: `.streamlit/secrets.toml.example` (add `[gmail]` section)
- Modify: `requirements.txt` (add `toml`)

**Interfaces:**
- Consumes: `select_exercises`'s return shape (list of dicts with `Exercise`, `Sets`, `Instructions`, `Example`, optionally `_repeat`); `MINUTES_PER_EXERCISE`, `TOTAL_MINUTES` from Task 2.
- Produces:
  - `load_local_secrets() -> dict | None` — loads `.streamlit/secrets.toml` via `toml.load()` if it exists, else `None`.
  - `build_email_html(workout_type: str, exercises: list[dict]) -> str`
  - `send_email(gmail_secrets: dict, subject: str, html_body: str) -> None` — `gmail_secrets` must have `sender_email` and `app_password` keys; raises on SMTP failure.

- [ ] **Step 1: Add `toml` to `requirements.txt`**

```
streamlit
requests
gspread
oauth2client
toml
```

- [ ] **Step 2: Add the `[gmail]` section to `.streamlit/secrets.toml.example`**

Append to the existing file:

```toml

[gmail]
sender_email = "theprofmeta@gmail.com"
app_password = "xxxx xxxx xxxx xxxx"  # Gmail App Password (not your real password) - generate at https://myaccount.google.com/apppasswords
```

- [ ] **Step 3: Append secrets-loading, email-building, and email-sending code to `workout_generator.py`**

```python
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import toml


def load_local_secrets():
    path = os.path.join('.streamlit', 'secrets.toml')
    if os.path.exists(path):
        return toml.load(path)
    return None


def build_email_html(workout_type, exercises):
    rows = []
    for i, ex in enumerate(exercises, start=1):
        label = f"{ex['Exercise']} (Round 2)" if ex.get('_repeat') else ex['Exercise']
        video_url = ex.get('Example', '')
        video_link = f'<p><a href="{video_url}">Watch demo</a></p>' if video_url else ''
        rows.append(f"""
            <div style="margin-bottom:16px;padding:12px;border-left:4px solid #667eea;">
                <h3 style="margin:0 0 4px 0;">{i}. {label}</h3>
                <p style="margin:2px 0;"><strong>Sets:</strong> {ex.get('Sets', '')}</p>
                <p style="margin:2px 0;"><strong>Time:</strong> {MINUTES_PER_EXERCISE} minutes</p>
                <p style="margin:2px 0;"><strong>Instructions:</strong> {ex.get('Instructions', '')}</p>
                {video_link}
            </div>
        """)
    return f"""
        <html><body>
        <h2>Your {TOTAL_MINUTES}-Minute {workout_type} Workout</h2>
        {''.join(rows)}
        </body></html>
    """


def send_email(gmail_secrets, subject, html_body):
    sender = gmail_secrets['sender_email']
    password = gmail_secrets['app_password']

    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From'] = sender
    msg['To'] = sender
    msg.attach(MIMEText(html_body, 'html'))

    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
        server.login(sender, password)
        server.sendmail(sender, [sender], msg.as_string())
```

- [ ] **Step 4: Verify email HTML builds correctly (no send)**

Run:
```bash
python -c "
from workout_generator import build_email_html

exercises = [
    {'Exercise': 'Plank', 'Sets': 3, 'Instructions': 'Hold as long as you can', 'Example': 'https://youtu.be/abc'},
    {'Exercise': 'Plank', 'Sets': 3, 'Instructions': 'Hold as long as you can', 'Example': 'https://youtu.be/abc', '_repeat': True},
]
html = build_email_html('Core', exercises)
assert 'Your 30-Minute Core Workout' in html
assert 'Plank (Round 2)' in html
assert 'https://youtu.be/abc' in html
assert html.count('Plank') == 3  # 'Plank' + 'Plank (Round 2)' + link text doesn't repeat name
print('OK')
"
```
Expected: `OK`

- [ ] **Step 5: Commit**

```bash
git add workout_generator.py requirements.txt .streamlit/secrets.toml.example
git commit -m "Add email composition and Gmail SMTP sending to workout plan generator"
```

---

### Task 4: CLI entry point

**Files:**
- Modify: `workout_generator.py` (append `main()` and the `if __name__ == '__main__':` block)

**Interfaces:**
- Consumes: `sheets_client.get_client`, `select_exercises`, `build_email_html`, `send_email`, `load_local_secrets` from Tasks 1-3.
- Produces: a runnable CLI — `python workout_generator.py --type "<type>" [--dry-run]`.

- [ ] **Step 1: Append the CLI wiring to `workout_generator.py`**

```python
import argparse
import sys

from sheets_client import get_client

SPREADSHEET_ID = "1CSokDhyaVLpc9tJgJDKD-y6G_ClmN7aRFrUL6xursro"


def main():
    parser = argparse.ArgumentParser(
        description="Generate and email a 30-minute, 6-exercise workout plan.")
    parser.add_argument('--type', required=True,
                         help='Workout type to filter by, e.g. "Upper Body", "Core"')
    parser.add_argument('--dry-run', action='store_true',
                         help='Print the email instead of sending it')
    args = parser.parse_args()

    secrets = load_local_secrets()
    client = get_client(secrets)
    if not client:
        print("Error: Google Sheets credentials not found. "
              "Configure service-account.json or .streamlit/secrets.toml.", file=sys.stderr)
        sys.exit(1)

    spreadsheet = client.open_by_key(SPREADSHEET_ID)
    all_records = spreadsheet.worksheet('exercises').get_all_records()

    try:
        selected = select_exercises(all_records, args.type)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    html_body = build_email_html(args.type, selected)
    subject = f"Your 30-Minute {args.type} Workout"

    if args.dry_run:
        print(f"Subject: {subject}\n")
        print(html_body)
        return

    if not secrets or 'gmail' not in secrets:
        print("Error: Gmail secrets not found. Add a [gmail] section to "
              ".streamlit/secrets.toml (see .streamlit/secrets.toml.example).", file=sys.stderr)
        sys.exit(1)

    try:
        send_email(secrets['gmail'], subject, html_body)
    except Exception as e:
        print(f"Error sending email: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"Workout plan emailed to {secrets['gmail']['sender_email']}.")


if __name__ == '__main__':
    main()
```

- [ ] **Step 2: Verify `--dry-run` end-to-end against the real sheet (no email sent)**

Run: `python workout_generator.py --type "Core" --dry-run`
Expected: prints `Subject: Your 30-Minute Core Workout` followed by HTML containing 6 `<h3>` blocks (some possibly labeled "(Round 2)", since the sheet currently has only 4 "Core" exercises)

- [ ] **Step 3: Verify the zero-match error path**

Run: `python workout_generator.py --type "Cardio" --dry-run`
Expected: exits non-zero, prints `Error: No exercises found with type 'Cardio'.` to stderr, no HTML printed

- [ ] **Step 4: Commit**

```bash
git add workout_generator.py
git commit -m "Add CLI entry point to workout plan generator"
```

---

### Task 5: Claude Code project skill

**Files:**
- Create: `.claude/skills/workout-plan/SKILL.md`

**Interfaces:**
- Consumes: `workout_generator.py`'s CLI (`--type`, `--dry-run`) from Task 4.

- [ ] **Step 1: Write `.claude/skills/workout-plan/SKILL.md`**

```markdown
---
name: workout-plan
description: Use when the user asks for a workout plan, workout email, or exercise routine by type (e.g. "give me a core workout", "send me an upper body workout") - generates a 6-exercise, 30-minute plan from the exercises Google Sheet and emails it
---

# Workout Plan Generator

Generates a 30-minute, 6-exercise workout plan filtered by type (e.g. "Core",
"Upper Body", "Lower Body", "Mobility", "Warmup") from the `exercises` Google
Sheet, and emails it to theprofmeta@gmail.com.

## Usage

1. Determine the workout type from the user's request. If it's ambiguous or
   not specified, ask which type they want.
2. Run from the project root (`vb/`):

   ```bash
   python workout_generator.py --type "<type>"
   ```

   Use `--dry-run` instead of sending (prints the composed email to the
   console) if the user wants to preview it first, or if you want to sanity
   check formatting without sending mail.

3. Report the script's own output back to the user verbatim-ish:
   - Success prints `Workout plan emailed to theprofmeta@gmail.com.`
   - Failure exits non-zero with an `Error: ...` message on stderr - surface
     that message to the user rather than claiming success. Common cases:
     - No exercises of that type exist yet in the sheet (`Error: No exercises
       found with type '<type>'.`) - suggest checking the `Type` column in
       the `exercises` worksheet, or trying a different type from Warmup /
       Upper Body / Lower Body / Core / Mobility.
     - Missing Gmail credentials (`Error: Gmail secrets not found...`) - the
       `[gmail]` section needs to be added to `.streamlit/secrets.toml` (see
       `.streamlit/secrets.toml.example`).
     - Missing Google Sheets credentials - `service-account.json` or the
       `[gcp_service_account]` secrets section needs to be configured.
```

- [ ] **Step 2: Verify the skill file is discoverable and well-formed**

Run: `python -c "import re; content = open('.claude/skills/workout-plan/SKILL.md').read(); assert content.startswith('---'); front = content.split('---')[1]; assert 'name: workout-plan' in front; assert 'description:' in front; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add .claude/skills/workout-plan/SKILL.md
git commit -m "Add workout-plan Claude Code project skill"
```

---

### Task 6: Documentation and final end-to-end check

**Files:**
- Modify: `CLAUDE.md` (document the new script/skill)

**Interfaces:**
- Consumes: everything from Tasks 1-5.

- [ ] **Step 1: Add a section to `CLAUDE.md` documenting the new script**

Insert after the "### Credentials" subsection, before "### `.kiro/steering/` docs":

```markdown
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
```

- [ ] **Step 2: Run the full manual regression pass**

Run each and confirm the expected behavior:

```bash
python workout_generator.py --type "Lower Body" --dry-run   # 6 exercises, no repeats (6 match today)
python workout_generator.py --type "core" --dry-run          # case-insensitive match works
python workout_generator.py --type "Cardio" --dry-run         # Error: No exercises found..., exit non-zero
python -c "import app"                                        # app.py still imports cleanly
```

- [ ] **Step 3: Send one real email to confirm SMTP works end-to-end**

Requires `.streamlit/secrets.toml` to have a real `[gmail]` `app_password`
(Gmail App Password) configured first — this step can't be verified until
that's set up locally.

Run: `python workout_generator.py --type "Core"`
Expected: prints `Workout plan emailed to theprofmeta@gmail.com.`; confirm the email arrives with 6 exercises, correct sets/instructions, and working "Watch demo" links.

- [ ] **Step 4: Commit**

```bash
git add CLAUDE.md
git commit -m "Document workout plan generator in CLAUDE.md"
```
