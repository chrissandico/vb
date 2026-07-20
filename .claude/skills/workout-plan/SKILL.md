---
name: workout-plan
description: Use when the user asks for a workout plan, workout email, or exercise routine by type (e.g. "give me a core workout", "send me an upper body workout") - generates a 6-exercise, 30-minute plan from the exercises Google Sheet and emails it
---

# Workout Plan Generator

Generates a 30-minute, 6-exercise workout plan filtered by type (e.g. "Core",
"Upper Body", "Lower Body", "Mobility", "Warmup") from the `exercises` Google
Sheet, and emails it to the recipient(s) configured in the `[gmail]` section
of `.streamlit/secrets.toml` (defaults to the sender's own address if no
`recipients` list is set).

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
   - Success prints `Workout plan emailed to <recipients>.`
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
     - Email send failure (`Error sending email: ...`) - the Sheets fetch and
       exercise selection succeeded, but Gmail SMTP rejected the send (e.g.
       wrong `app_password`, revoked App Password, or a network issue) -
       suggest checking the `[gmail]` app_password in `.streamlit/secrets.toml`
       is a valid Gmail App Password, not the real account password.
