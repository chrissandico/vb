---
inclusion: always
---

# Project Structure

## Root Files

- `app.py`: Main Streamlit application entry point
  - Handles UI rendering and user interactions
  - Makes API calls to AWS Lambda backend
  - Displays tasks, workouts, and bonus activities

- `hash.py`: Utility script for generating bcrypt password hashes
  - Used to create hashed passwords for `credentials.yaml`
  - Run manually when updating user credentials

- `credentials.yaml`: User authentication configuration
  - Stores user profiles (username, email, name, hashed password)
  - Cookie configuration for session management
  - Preauthorized email list

- `README.md`: Project documentation (minimal)

## Code Organization

The project follows a simple flat structure with:
- Single-file Streamlit app (`app.py`)
- Utility scripts at root level
- Configuration files at root level

## Key Functions

- `get_sheets_client()`: Initializes and caches Google Sheets API client
- `fetch_activities(name)`: Fetches tasks and exercises from Google Sheets
- `main()`: Streamlit UI logic and event handling

## Data Source

Activities are stored in Google Sheets with the following structure:
- **poppies** sheet: Tasks with columns (Task Name, Task Description, Type, Duration)
- **exercises** sheet: Exercises with columns (Exercise, Sets, Instructions, Example, Type)
- **history** sheet: Historical activity log
