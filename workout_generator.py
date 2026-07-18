"""Generate a 30-minute, 6-exercise workout plan by type and email it."""
import os
import random
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import toml

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
