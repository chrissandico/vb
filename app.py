import requests
import streamlit as st
import streamlit_authenticator as stauth
import bcrypt
import yaml
from yaml.loader import SafeLoader

# API Gateway URL for your Lambda function
API_GATEWAY_URL = "https://qsh7ju1xd0.execute-api.us-east-1.amazonaws.com/test/vb"

with open('credentials.yaml') as file:
    config = yaml.load(file, Loader=SafeLoader)

authenticator = stauth.Authenticate(
    config['credentials'],
    config['cookie']['name'],
    config['cookie']['key'],
    config['cookie']['expiry_days'],
    config['preauthorized']
)

# Define the fields for the login form
#fields = {
#    "username": "Username",
#    "password": "Password",
#    "submit_button": "Login"
#}

# Authentication logic
#name, authentication_status, username = authenticator.login('Login', fields)

authenticator.login()


if st.session_state["authentication_status"]:
    # Authenticated, show app content
    def trigger_lambda(name):
        payload = {"user": name}
        response = requests.post(API_GATEWAY_URL, json=payload)
        try:
            data = response.json()
        except ValueError as e:
            st.error(f"Error parsing response: {e}")
            return None
        return data

    def main():
        st.title("Fun Things To Do")
        
        name = st.radio("Select a name", ["Preston", "Isaac"])

        # Submit button
        if st.button("Submit"):
            with st.spinner('Retrieving tasks...'):
                result = trigger_lambda(name)
            if result:
                st.balloons()
                # Display the selected tasks as a numbered list
                st.subheader("For " + name)
                for i, task in enumerate(result['selected_tasks'], start=1):
                    task_label = f"{i}. {task['name']} ({task['duration']} minutes) - {task['description']}"
                    st.write(task_label)

                # Display the random task
                st.subheader("Random Task")
                if result['random_task']:
                    st.write(f"- {result['random_task']['name']} ({result['random_task']['duration']} minutes) - {result['random_task']['description']}")
                else:
                    st.write("No random task available.")
            else:
                st.warning("Failed to retrieve tasks.")

    main()

elif st.session_state["authentication_status"] is False:
    st.error('Username/password is incorrect')
elif st.session_state["authentication_status"] is None:
    st.warning('Please enter your username and password')
