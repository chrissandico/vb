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

def extract_youtube_id(url):
    """Extract YouTube video ID from various URL formats"""
    if not url or not isinstance(url, str):
        return None
    
    # Handle youtu.be format
    if 'youtu.be/' in url:
        return url.split('youtu.be/')[-1].split('?')[0]
    # Handle youtube.com format
    elif 'youtube.com/watch?v=' in url:
        return url.split('v=')[-1].split('&')[0]
    # Handle embed format
    elif 'youtube.com/embed/' in url:
        return url.split('embed/')[-1].split('?')[0]
    
    return None

def main():
    # Page config for better styling
    st.set_page_config(page_title="Daily Activities", page_icon="🎯", layout="wide")
    
    # Custom CSS for better styling
    st.markdown("""
        <style>
        .main-title {
            text-align: center;
            font-size: 3rem;
            font-weight: bold;
            margin-bottom: 2rem;
            background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        .task-card {
            background-color: #ffffff;
            padding: 1.5rem;
            border-radius: 10px;
            margin-bottom: 1rem;
            border-left: 5px solid #667eea;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            color: #1f1f1f;
        }
        .task-card h4 {
            color: #1f1f1f;
            margin-bottom: 0.5rem;
        }
        .task-card p {
            color: #333333;
            margin: 0.3rem 0;
        }
        .exercise-card {
            background-color: #ffffff;
            padding: 1.5rem;
            border-radius: 10px;
            margin-bottom: 1.5rem;
            border-left: 5px solid #764ba2;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            color: #1f1f1f;
        }
        .exercise-card h4 {
            color: #1f1f1f;
            margin-bottom: 0.5rem;
        }
        .exercise-card p {
            color: #333333;
            margin: 0.3rem 0;
        }
        .bonus-card {
            background-color: #ffffff;
            padding: 1.5rem;
            border-radius: 10px;
            border-left: 5px solid #ff9800;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            color: #1f1f1f;
        }
        .bonus-card h4 {
            color: #1f1f1f;
            margin-bottom: 0.5rem;
        }
        .bonus-card p {
            color: #333333;
            margin: 0.3rem 0;
        }
        </style>
    """, unsafe_allow_html=True)
    
    st.markdown('<h1 class="main-title">🎯 Daily Activities</h1>', unsafe_allow_html=True)
    
    # Centered name selection
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        name = st.radio("Who's ready for today?", ["Preston", "Isaac"], horizontal=True)
        submit_button = st.button("🚀 Get My Activities", use_container_width=True, type="primary")

    # Submit button
    if submit_button:
        with st.spinner('✨ Creating your personalized list...'):
            result = fetch_activities(name)
        
        if result:
            st.balloons()
            st.markdown("---")
            
            # Display tasks section
            st.markdown(f"### 📋 Tasks for {name}")
            for i, task in enumerate(result.get('selected_tasks', []), start=1):
                with st.container():
                    st.markdown(f"""
                        <div class="task-card">
                            <h4>{i}. {task['name']}</h4>
                            <p><strong>⏱️ Duration:</strong> {task['duration']} minutes</p>
                            <p>{task['description']}</p>
                        </div>
                    """, unsafe_allow_html=True)
            
            st.markdown("---")
            
            # Display workout section
            st.markdown("### 💪 Today's Workout")
            for i, exercise in enumerate(result.get('selected_exercises', []), start=1):
                with st.container():
                    st.markdown(f"""
                        <div class="exercise-card">
                            <h4>{i}. {exercise['exercise']}</h4>
                            <p><strong>🔢 Sets:</strong> {exercise['sets']}</p>
                            <p><strong>📝 Instructions:</strong> {exercise['instructions']}</p>
                        </div>
                    """, unsafe_allow_html=True)
                    
                    # Embed YouTube video if available
                    video_url = exercise.get('video', '')
                    video_id = extract_youtube_id(video_url)
                    
                    if video_id:
                        col1, col2, col3 = st.columns([1, 2, 1])
                        with col2:
                            st.video(f"https://www.youtube.com/watch?v={video_id}")
                    elif video_url:
                        st.info(f"📺 [Watch demonstration]({video_url})")
                    
                    st.markdown("<br>", unsafe_allow_html=True)
            
            st.markdown("---")
            
            # Display bonus task
            st.markdown("### 🎁 Bonus Challenge")
            random_task = result.get('random_task')
            if random_task:
                st.markdown(f"""
                    <div class="bonus-card">
                        <h4>{random_task['name']}</h4>
                        <p><strong>⏱️ Duration:</strong> {random_task['duration']} minutes</p>
                        <p>{random_task['description']}</p>
                    </div>
                """, unsafe_allow_html=True)
            else:
                st.info("No bonus task available today.")
        else:
            st.error("❌ Failed to retrieve activities. Please try again.")

if __name__ == "__main__":
    main()