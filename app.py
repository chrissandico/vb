import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import random
import json
import os

# Google Sheets configuration
SPREADSHEET_ID = "1CSokDhyaVLpc9tJgJDKD-y6G_ClmN7aRFrUL6xursro"

@st.cache_resource
def get_sheets_client():
    """Initialize and cache the Google Sheets client"""
    scope = ['https://spreadsheets.google.com/feeds',
             'https://www.googleapis.com/auth/drive']
    
    # Try to load from Streamlit secrets first (for cloud deployment)
    if hasattr(st, 'secrets') and 'gcp_service_account' in st.secrets:
        creds = ServiceAccountCredentials.from_json_keyfile_dict(
            st.secrets['gcp_service_account'], scope)
    # Fall back to local file (for local development)
    elif os.path.exists('service-account.json'):
        creds = ServiceAccountCredentials.from_json_keyfile_name(
            'service-account.json', scope)
    else:
        st.error("Google Sheets credentials not found. Please configure secrets.")
        return None
    
    return gspread.authorize(creds)

def fetch_activities(name):
    """Fetch activities from Google Sheets for the specified user"""
    try:
        client = get_sheets_client()
        if not client:
            return None
        
        spreadsheet = client.open_by_key(SPREADSHEET_ID)
        
        # Get tasks and exercises sheets
        tasks_sheet = spreadsheet.worksheet('poppies')
        exercises_sheet = spreadsheet.worksheet('exercises')
        
        # Get all records as list of dictionaries
        all_tasks = tasks_sheet.get_all_records()
        all_exercises = exercises_sheet.get_all_records()
        
        # Filter out empty rows
        tasks = [t for t in all_tasks if t.get('Task Name')]
        exercises = [e for e in all_exercises if e.get('Exercise')]
        
        # Select random tasks and exercises
        num_tasks = min(5, len(tasks))
        num_exercises = min(5, len(exercises))
        
        selected_tasks = random.sample(tasks, num_tasks) if tasks else []
        selected_exercises = random.sample(exercises, num_exercises) if exercises else []
        
        # Pick a random bonus task (different from selected tasks)
        remaining_tasks = [t for t in tasks if t not in selected_tasks]
        random_task = random.choice(remaining_tasks) if remaining_tasks else None
        
        # Format the response to match expected structure
        return {
            'selected_tasks': [
                {
                    'name': t['Task Name'],
                    'duration': t['Duration'],
                    'description': t['Task Description']
                } for t in selected_tasks
            ],
            'selected_exercises': [
                {
                    'exercise': e['Exercise'],
                    'sets': e['Sets'],
                    'instructions': e['Instructions'],
                    'video': e['Example']
                } for e in selected_exercises
            ],
            'random_task': {
                'name': random_task['Task Name'],
                'duration': random_task['Duration'],
                'description': random_task['Task Description']
            } if random_task else None
        }
    except Exception as e:
        st.error(f"Error fetching data from Google Sheets: {e}")
        return None

def main():
    st.title("Fun Things To Do")
    
    # Get user input
    name = st.radio("Select a name", ["Preston", "Isaac"])

    # Submit button
    if st.button("Submit"):
        with st.spinner('Putting the list together...!'):
            result = fetch_activities(name)
        if result:
            st.balloons()
            # Display the selected tasks as a numbered list
            st.subheader("For " + name)
            for i, task in enumerate(result.get('selected_tasks', []), start=1):
                task_label = f"{i}. {task['name']} ({task['duration']} minutes) - {task['description']}"
                st.write(task_label)

            # Display the workout
            st.subheader("Your workout for the day")
            for i, exercise in enumerate(result.get('selected_exercises', []), start=1):
                exercise_label = f"{i}. {exercise['exercise']} ({exercise['sets']} sets) - {exercise['instructions']} - {exercise['video']}"
                st.write(exercise_label)

            # Display the random task
            st.subheader("Bonus Task")
            random_task = result.get('random_task')
            if random_task:
                st.write(f"- {random_task['name']} ({random_task['duration']} minutes) - {random_task['description']}")
            else:
                st.write("No random task available.")
        else:
            st.warning("Failed to retrieve tasks.")

if __name__ == "__main__":
    main()