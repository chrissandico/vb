import requests
import streamlit as st
import streamlit.components.v1 as components


# API Gateway URL for your Lambda function
API_GATEWAY_URL = "https://qsh7ju1xd0.execute-api.us-east-1.amazonaws.com/test/vb"

def trigger_lambda(name):
    payload = {"user": name}
    #st.write(payload)
    response = requests.post(API_GATEWAY_URL, json=payload)
    #st.write(response.content)
    try:
        data = response.json()        
    except ValueError as e:
        st.error(f"Error parsing response: {e}")
        return None
    return data

def main():
    st.title("Fun Things To Do")
    
    # Get user input
    name = st.radio("Select a name", ["Preston", "Isaac"])

    # Submit button
    if st.button("Submit"):
        with st.spinner('Putting the list together...!'):
            result = trigger_lambda(name)
        if result:
            st.balloons()
            # Display the selected tasks as a numbered list
            st.subheader("For " + name)
            for i, task in enumerate(result['selected_tasks'], start=1):
                task_label = f"{i}. {task['name']} ({task['duration']} minutes) - {task['description']}"
                st.write(task_label)

            # Display the workout
            st.subheader("Your workout for the day")
            for i, exercise in enumerate(result['selected_exercises'], start=1):
                exercise_label = f"{i}. {exercise['exercise']} ({exercise['sets']} sets) - {exercise['instructions']} - {exercise['video']}"
                st.write(exercise_label)

            # Display the random task
            st.subheader("Bonus Task")
            if result['random_task']:
                st.write(f"- {result['random_task']['name']} ({result['random_task']['duration']} minutes) - {result['random_task']['description']}")
            else:
                st.write("No random task available.")
        else:
            st.warning("Failed to retrieve tasks.")

if __name__ == "__main__":
    main()