---
inclusion: always
---

# Tech Stack

## Core Technologies

- **Python**: Primary programming language
- **Streamlit**: Web application framework for the UI
- **Google Sheets API**: Data source for tasks and exercises

## Key Libraries

- `streamlit`: Web UI framework
- `gspread`: Google Sheets API client
- `oauth2client`: Google API authentication
- `bcrypt`: Password hashing for authentication

## Configuration

- `credentials.yaml`: User authentication with bcrypt-hashed passwords
- `service-account.json`: Google Sheets API credentials (not in repo)
- Google Spreadsheet ID: `1CSokDhyaVLpc9tJgJDKD-y6G_ClmN7aRFrUL6xursro`
- Service account: `virtual-summer-tasks@virtual-babysitter.iam.gserviceaccount.com`

## Common Commands

```bash
# Run the Streamlit application
streamlit run app.py

# Generate password hashes (for credentials.yaml)
python hash.py
```

## Authentication

- Uses bcrypt for password hashing
- Credentials stored in `credentials.yaml` with hashed passwords
- Cookie-based session management (30-day expiry)
