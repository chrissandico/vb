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
