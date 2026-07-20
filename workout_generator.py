"""Generate a 30-minute, 6-exercise workout plan by type and email it."""
import argparse
import os
import random
import smtplib
import sys
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import toml

from sheets_client import get_client

SPREADSHEET_ID = "1CSokDhyaVLpc9tJgJDKD-y6G_ClmN7aRFrUL6xursro"

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
    if zero rows match. Every returned entry is a shallow copy of its source
    row dict, so mutating a returned entry never affects all_records.
    """
    wanted = workout_type.strip().lower()
    matches = [
        r for r in all_records
        if wanted in [t.lower() for t in parse_types(r.get('Type', ''))]
    ]

    if not matches:
        raise ValueError(f"No exercises found with type '{workout_type}'.")

    if len(matches) >= NUM_EXERCISES:
        return [dict(r) for r in random.sample(matches, NUM_EXERCISES)]

    selected = [dict(r) for r in matches]
    random.shuffle(selected)
    pool = list(matches)
    random.shuffle(pool)
    i = 0
    while len(selected) < NUM_EXERCISES:
        repeat = dict(pool[i % len(pool)])
        repeat['_repeat'] = True
        selected.append(repeat)
        i += 1
    return selected


def load_local_secrets():
    path = os.path.join('.streamlit', 'secrets.toml')
    if os.path.exists(path):
        return toml.load(path)
    return None


def build_email_html(workout_type, exercises):
    rows = []
    for i, ex in enumerate(exercises, start=1):
        label = f"{ex['Exercise']} (again!)" if ex.get('_repeat') else ex['Exercise']
        video_url = ex.get('Example', '')
        video_link = (
            f'<p style="margin:10px 0 0 0;">'
            f'<a href="{video_url}" style="display:inline-block;background-color:#667eea;'
            f'color:#ffffff;padding:8px 18px;border-radius:20px;text-decoration:none;'
            f'font-weight:bold;font-size:15px;">&#9654; Watch how</a></p>'
        ) if video_url else ''
        major_muscles = ex.get('Major Muscles', '')
        minor_muscles = ex.get('Minor Muscles', '')
        muscle_bits = []
        if major_muscles:
            muscle_bits.append(f'<strong>Main:</strong> {major_muscles}')
        if minor_muscles:
            muscle_bits.append(f'<strong>Also:</strong> {minor_muscles}')
        muscle_line = (
            f'<p style="margin:6px 0 0 0;font-size:14px;color:#777777;">'
            f'&#127919; {"&nbsp;&nbsp;&nbsp;".join(muscle_bits)}</p>'
        ) if muscle_bits else ''
        rows.append(f"""
            <div style="margin-bottom:18px;padding:16px;border-radius:12px;
                        border-left:6px solid #667eea;background-color:#f7f7fb;">
                <p style="margin:0 0 8px 0;font-size:20px;color:#333333;">
                    <span style="color:#667eea;">&#9744;</span> <strong>{i}. {label}</strong>
                </p>
                <p style="margin:2px 0;font-size:16px;color:#555555;">
                    &#128257; {ex.get('Sets', '')} sets &nbsp;&nbsp; &#9200; {MINUTES_PER_EXERCISE} min
                </p>
                <p style="margin:6px 0 0 0;font-size:16px;color:#333333;">{ex.get('Instructions', '')}</p>
                {muscle_line}
                {video_link}
            </div>
        """)
    return f"""
        <html><body style="font-family:Arial, Helvetica, sans-serif;">
        <h1 style="text-align:center;color:#667eea;font-size:26px;">
            &#127919; Your {TOTAL_MINUTES}-Minute {workout_type} Workout!
        </h1>
        <p style="text-align:center;font-size:16px;color:#555555;">
            Check off each one as you finish it &mdash; you've got this! &#128170;
        </p>
        {''.join(rows)}
        <p style="text-align:center;font-size:18px;color:#667eea;margin-top:10px;">
            &#127775; Awesome job! See you next workout! &#127775;
        </p>
        </body></html>
    """


def send_email(gmail_secrets, subject, html_body):
    sender = gmail_secrets['sender_email']
    password = gmail_secrets['app_password']
    recipients = gmail_secrets.get('recipients') or [sender]

    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From'] = sender
    msg['To'] = ', '.join(recipients)
    msg.attach(MIMEText(html_body, 'html'))

    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
        server.login(sender, password)
        server.sendmail(sender, recipients, msg.as_string())


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

    try:
        spreadsheet = client.open_by_key(SPREADSHEET_ID)
        all_records = spreadsheet.worksheet('exercises').get_all_records()
    except Exception as e:
        print(f"Error fetching exercises: {e}", file=sys.stderr)
        sys.exit(1)

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

    recipients = secrets['gmail'].get('recipients') or [secrets['gmail']['sender_email']]
    print(f"Workout plan emailed to {', '.join(recipients)}.")


if __name__ == '__main__':
    main()
