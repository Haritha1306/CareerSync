import streamlit as st
import pandas as pd
import logging
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import random
import time
import os
from fuzzywuzzy import process
import datetime
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import sounddevice as sd
import queue
import soundfile as sf
import speech_recognition as sr
import google.generativeai as genai

# Set page configuration
st.set_page_config(
    page_title="CareerSync",
    layout="wide"
)

# Custom CSS for styling the navigation bar
st.markdown("""
    <style>
        .nav-container {
            background-color: #4CAF50;  /* Green background color */
            padding: 10px 0;
            border-radius: 10px;
            margin-top: 0;  /* Ensure no margin on top */
        }
        .nav-btn {
            background-color: #ffffff;
            color: #4CAF50;
            border: 2px solid #4CAF50;
            padding: 10px 20px;
            border-radius: 5px;
            font-size: 16px;
            transition: background-color 0.3s, color 0.3s;
            width: 100%;  /* Button takes full column width */
        }
        .nav-btn:hover {
            background-color: #45a049;
            color: white;
        }
        .nav-btn.active {
            background-color: #45a049;  /* Active button color */
            color: white;
        }
        .container-fluid {
            margin-top: 20px;  /* Add space between navbar and page content */
        }
    </style>
""", unsafe_allow_html=True)

# Create a stationary navigation bar
nav = st.container()
with nav:
    # Applying the custom class to the navigation container
    st.markdown('<div class="nav-container">', unsafe_allow_html=True)
    
    # Creating columns with proper layout
    cols = st.columns([1, 1, 1])
    
    # Job Search Button
    with cols[0]:
        if st.button("Job Search", key="job_search", help="Go to Job Search", use_container_width=True):
            st.session_state['current_page'] = "Job Search"
            st.session_state['button_state'] = 'job_search'
        
    # Schedule Courses Button
    with cols[1]:
        if st.button("Schedule Courses", key="schedule_courses", help="Go to Schedule Courses", use_container_width=True):
            st.session_state['current_page'] = "Schedule Courses"
            st.session_state['button_state'] = 'schedule_courses'
        
    # Mock Interview Button
    with cols[2]:
        if st.button("Mock Interview", key="mock_interview", help="Go to Mock Interview", use_container_width=True):
            st.session_state['current_page'] = "Mock Interview"
            st.session_state['button_state'] = 'mock_interview'

    st.markdown('</div>', unsafe_allow_html=True)

# Default to the first page if no session state is set
if 'current_page' not in st.session_state:
    st.session_state['current_page'] = "Job Search"

# Display content based on selected page
st.markdown("<h1 style = 'text-align: center; color: lightBlue;'>CareerSync</h1>", unsafe_allow_html=True)
st.markdown("<h3 style = 'text-align: center;'>Welcome to the Job Search Tool. Lets find your dream job!! </h3>", unsafe_allow_html=True)
if st.session_state['current_page'] == "Job Search":
    st.title("🔍 Job Search ")
    logging.basicConfig(filename="scraping.log", level=logging.INFO)


    def setup_driver(headless=True):
        """Initialize and return a configured Selenium WebDriver."""
        options = webdriver.ChromeOptions()
        options.add_argument("--start-maximized")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64)")
        if headless:
            options.add_argument("--headless")
        try:
            service = Service('chromedriver.exe')  # Update path if needed
            driver = webdriver.Chrome(service=service, options=options)
        except Exception as e:
            raise RuntimeError(f"Error setting up WebDriver: {e}")
        return driver


    def scrape_linkedin_jobs(driver, job_title: str, location: str, num_jobs: int = 10) -> list:
        """
        Scrape job listings from LinkedIn based on job title and location, limited to the specified number of jobs.
        """
        logging.info(f'Starting LinkedIn job scrape for "{job_title}" in "{location}"...')
        jobs = []
        while True:
            driver.get(
                f"https://www.linkedin.com/jobs/search/?keywords={job_title}&location={location}"
            )

            if driver.title not in ["Sign Up | LinkedIn", "www.linkedin.com", ""]:
                break

        while len(jobs) < num_jobs:
            soup = BeautifulSoup(driver.page_source, "html.parser")
            job_listings = soup.find_all(
                "div",
                class_="base-card relative w-full hover:no-underline focus:no-underline base-card--link base-search-card base-search-card--link job-search-card",
            )
            for job in job_listings:
                if len(jobs) >= num_jobs:
                    break

                try:
                    job_title = job.find("h3", class_="base-search-card__title").text.strip()
                    job_company = job.find("h4", class_="base-search-card__subtitle").text.strip()
                    job_location = job.find("span", class_="job-search-card__location").text.strip()
                    apply_link = job.find("a", class_="base-card__full-link")["href"]

                    # Navigate to job details page
                    driver.get(apply_link)
                    time.sleep(random.uniform(0.5, 1.5))

                    description_soup = BeautifulSoup(driver.page_source, "html.parser")
                    job_description = description_soup.find(
                        "div", class_="description__text description__text--rich"
                    )
                    job_description = job_description.text.strip() if job_description else None
                    job_requirements = None

                    # Extract key requirements from description
                    if job_description:
                        for keyword in ["Requirements", "Qualifications", "Skills", "Responsibilities", "Eligibility"]:
                            if keyword.lower() in job_description.lower():
                                start_index = job_description.lower().find(keyword.lower())
                                job_requirements = job_description[start_index:].split('\n')[:5]
                                job_requirements = ' '.join(job_requirements).replace("Show more", "").replace("Show less", "")
                                break

                    # Add job to the list
                    jobs.append({
                        "title": job_title,
                        "company": job_company,
                        "location": job_location,
                        "link": apply_link,
                    })
                    logging.info(f'Scraped "{job_title}" at {job_company} in {job_location}.')

                except Exception as e:
                    logging.error(f"Error scraping job: {e}")

            # Scroll down to load more jobs
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)

        return jobs


    # Streamlit UI
    st.markdown(
        """
        <style>
        body {
            background-color: #4b4b4b;  /* Change to your desired background color */
        }
        .highlight {
            color: #add8e6; /* Example color that pops */
            font-weight: bold;
        }
        .headi { color:  #ffffff; font-weight: bold;}
        </style>
        """,
        unsafe_allow_html=True
    )

    

    # Step 1: Collect user inputs
    job_title = st.text_input("Enter Job Title:")
    job_location = st.text_input("Enter Job Location:")
    num_jobs = st.number_input("Number of Jobs to Scrape (default 10):", min_value=1, max_value=100, value=10, step=1)
    if st.button("Find Jobs"):
        if job_title and job_location:
            driver = setup_driver(headless=True)  # Run in headless mode
            max_retries = 3  # Fixed retry attempts
            attempt = 0
            job_data = []

            while attempt < max_retries:
                try:
                    logging.info(f"Attempt {attempt + 1} to scrape jobs...")
                    job_data = scrape_linkedin_jobs(driver, job_title, job_location, num_jobs=num_jobs)
                    if job_data:  # If jobs are found, break out of the retry loop
                        break
                except Exception as e:
                    logging.error(f"Error on attempt {attempt + 1}: {str(e)}")
                attempt += 1

            if job_data:
                job_df = pd.DataFrame(job_data)
                job_df.to_csv("jobs.csv", index=False)
                st.session_state['job_df'] = job_df  # Persist job data
                st.write("Job Results:")
                st.dataframe(job_df)
            else:
                st.error(f"No jobs found after {max_retries} attempts. Please try again with different inputs.")

            driver.quit()
        else:
            st.warning("Please enter both job title and location.")

    def read_skills_from_csv(file_path="skills_grouped.csv"):
        """
        Read the skills from a CSV file and return them as a dictionary with job roles as keys.
        """
        try:
            skills_df = pd.read_csv(file_path)
            if 'Job Role' in skills_df.columns and 'Skills' in skills_df.columns:
                skills_by_role = skills_df.set_index('Job Role')['Skills'].apply(lambda x: set(x.split(", "))).to_dict()
                return skills_by_role
            else:
                st.error(f"CSV file must have 'Job Role' and 'Skills' columns. Columns found: {skills_df.columns}")
                return {}
        except FileNotFoundError:
            st.error(f"CSV file not found at {file_path}.")
            return {}


    def find_missing_skills(user_skills, required_skills):
        user_skills_set = {skill.strip().lower() for skill in user_skills.split(",")}
        required_skills_set = {skill.strip().lower() for skill in required_skills}
        missing_skills = required_skills_set - user_skills_set
        return missing_skills

    course_path = 'courses.csv'
    courses_df = pd.read_csv(course_path)

    # Knapsack algorithm for course recommendation
    def knapsack(courses, max_courses=5):
        n = len(courses)
        dp = [[0] * (max_courses + 1) for _ in range(n + 1)]

        for i in range(1, n + 1):
            for w in range(1, max_courses + 1):
                rating = courses.iloc[i-1]['rating']
                reviews = courses.iloc[i-1]['num_reviews']
                value = rating * (reviews ** 0.5)  # Adjusted value based on reviews

                if w >= 1:  # If we can include this course
                    dp[i][w] = max(dp[i-1][w], dp[i-1][w-1] + value)
                else:
                    dp[i][w] = dp[i-1][w]

        selected_courses = []
        w = max_courses
        for i in range(n, 0, -1):
            if dp[i][w] != dp[i-1][w]:  # This course was included
                selected_courses.append(courses.iloc[i-1])
                w -= 1

        return selected_courses[::-1]  # Reverse to maintain the order of selection


    def recommend_courses(missing_skills, num_courses=5):  # Check the top 5 courses
        course_recommendations = {}
        
        for skill in missing_skills:
            skill_courses = courses_df[courses_df['title'].str.contains(skill, case=False, na=False, regex=False)]

            
            # Sort by rating and number of reviews, taking top 5 for Knapsack
            skill_courses = skill_courses.sort_values(by=['rating', 'num_reviews'], ascending=False).head(5)
            
            # Use the knapsack algorithm to select the best courses
            recommended_courses = knapsack(skill_courses, num_courses)

            # Select only the best course
            if recommended_courses:
                best_course = recommended_courses[0]  # Get the highest rated course
                course_recommendations[skill] = best_course  # Store the best course for the skill
        
        return course_recommendations
    # User input for skills
    user_skills = st.text_input("Please enter your skills, separated by commas (e.g., python, javascript, sql):")

    skill_sets = read_skills_from_csv("skills_grouped.csv")

    if st.button("Get Recommendations"):
        if 'job_df' in st.session_state:  # Check if job data exists in session state
            st.write("Previously Scraped Job Results:")
            st.dataframe(st.session_state['job_df'])
        if user_skills:
            all_missing_skills = set()

            # Read job data
            file_path = 'jobs.csv'
            jobs_df = pd.read_csv(file_path)

        if 'job_df' in st.session_state:
                job_df = st.session_state['job_df']  # Retrieve job data
                all_missing_skills = set()

                for _, row in job_df.iterrows():
                        job_title = row['title']
                        best_match = process.extractOne(job_title, skill_sets.keys())
                        matched_job_title = best_match[0] if best_match[1] >= 80 else None

                        if matched_job_title:
                            required_skills = skill_sets[matched_job_title]
                            missing_skills = find_missing_skills(user_skills, required_skills)
                            all_missing_skills.update(missing_skills)

                if all_missing_skills:
                    st.write(f"Skills You Currently Lack:\n {', '.join(all_missing_skills)}")
                    recommended_courses = recommend_courses(all_missing_skills)


                # Recommend courses for missing skills
                recommended_courses = recommend_courses(all_missing_skills)
                if 'recommended_courses' not in st.session_state:
                    st.session_state['recommended_courses'] = recommended_courses
                recommended_courses = st.session_state['recommended_courses']
                # Display recommended courses

                st.write("### Recommended Courses")
                for skill, course in recommended_courses.items():
                    st.subheader(f"Top Course for Skill: {skill}")
                    if course is not None and not course.empty:
                        st.write(f"""- **Title:** {course['title']}  
                                **URL:** [Link]({"https://udemy.com" + course['url']})
                                **Rating:** {course['rating']}  
                                **Reviews:** {course['num_reviews']}  
                                **Last Update:** {course['last_update_date']}  
                                **Duration:** {course['duration']} """)
                    else:
                        st.write(f"No recommended course found for skill: {skill}")
        else:
            st.write("### Missing Skills: None")
    else:
        st.info("Run a job search to see missing skills and recommendations.")

elif st.session_state['current_page'] == "Schedule Courses":
    st.title("📚 Schedule Courses ")
    

    SCOPES = ['https://www.googleapis.com/auth/calendar']
    YOUR_TIMEZONE = 'Asia/Kolkata'  # Update to your timezone

    def parse_duration(duration_str):
        """
        Extract numeric hours from a duration string like '6.5 total hours'.
        Returns 0.0 if parsing fails.
        """
        try:
            # Extract the numeric portion of the string
            return float(''.join(c for c in duration_str if c.isdigit() or c == '.'))
        except ValueError:
            st.error(f"Invalid duration format: {duration_str}")
            return 0.0  # Default to 0.0 if parsing fails

    def get_user_calendar_service(user_email):
        """Authenticate the user and return the Google Calendar service."""
        creds = None
        token_file = f'{user_email}_token.json'
        if os.path.exists(token_file):
            creds = Credentials.from_authorized_user_file(token_file, SCOPES)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
                creds = flow.run_local_server(port=0)

            with open(token_file, 'w') as token:
                token.write(creds.to_json())

        service = build('calendar', 'v3', credentials=creds)
        return service

    def schedule_courses(service, selected_courses, study_time, available_hours, user_email):
        """Schedule the selected courses based on user input."""
        start_date = datetime.datetime.now()
        # weekly_hours = available_hours
        # Ensure weekly_hours is an integer
        weekly_hours = int(available_hours)  # Force convert to an integer

        # Debug: Check the type of weekly_hours and course['duration']
        # st.write(f"Debug: weekly_hours is {weekly_hours}, type: {type(weekly_hours)}")
        # for course in selected_courses:
        #     st.write(f"Debug: course['duration'] is {course['duration']}, type: {type(course['duration'])}")

        # Calculate total sessions per course (round the result)
        total_sessions_per_course = [
            round(-(float(course['duration']) // -weekly_hours)) for course in selected_courses
        ]

        # Total sessions needed for each course
        # total_sessions_per_course = [
        #     [round(-(course['duration'] // -weekly_hours)) for course in selected_courses]

        # ]  
        print(total_sessions_per_course)# Ceiling division

        study_slot = {"morning": datetime.time(7, 0), "evening": datetime.time(15, 0), "night": datetime.time(21, 0)}
        start_time = study_slot.get(study_time, datetime.time(7, 0))
        end_time = datetime.time(min(start_time.hour + 3, 23), 0)  # Ensure end time does not exceed 11 PM

        day_count = 0
        
        for course_index, (course, total_sessions_per_course) in enumerate(zip(selected_courses, total_sessions_per_course)):
            hours_per_session = min(course['duration'], weekly_hours)
            course_hours_left = course['duration']
            course_start_time = datetime.datetime.combine(start_date + datetime.timedelta(days=day_count), start_time)
            for total_sessions_per_course in range(total_sessions_per_course):
                if day_count % 2 == 0:  # Schedule on alternating days
                    event_date = start_date + datetime.timedelta(days=day_count)
                    event_start = course_start_time
                    event_end = event_start + datetime.timedelta(hours=hours_per_session)

                    # Create and insert the event in Google Calendar
                    event = {
                        'summary': course['title'],
                        'description': f"Study session for {course['title']}",
                        'start': {
                            'dateTime': event_start.isoformat(),
                            'timeZone': YOUR_TIMEZONE,
                        },
                        'end': {
                            'dateTime': event_end.isoformat(),
                            'timeZone': YOUR_TIMEZONE,
                        },
                    }

                    created_event = service.events().insert(calendarId='primary', body=event).execute()
                    st.write(f"Event created: [Link to Calendar]({created_event.get('htmlLink')}) for {course['title']} on {event_start.strftime('%Y-%m-%d %H:%M')}")
                    course_start_time += datetime.timedelta(hours=1)
                    course_hours_left -= hours_per_session
                    if course_hours_left <= 0:
                        break

                day_count += 1

    def course_scheduler_ui():
        """Streamlit UI for scheduling courses."""

        if "recommended_courses" not in st.session_state or not st.session_state["recommended_courses"]:
            st.warning("No recommended courses found! Please generate recommendations on the main page.")
            return

        st.write("Debug: Recommended Courses Structure:")
        st.write(st.session_state["recommended_courses"])

        user_email = st.text_input("Enter your Email ID:", "")
        study_time = st.radio("Select your preferred study time:", ["morning", "evening", "night"])
        available_hours = st.radio("How many hours can you study per week?", [1, 2, 3, 4, 6, 7, 8])
        

        st.write("### Select Courses to Schedule:")
        recommended_courses = st.session_state["recommended_courses"]
        selected_courses = []

        for skill, course in recommended_courses.items():
            st.subheader(f"Top Course for Skill: {skill}")
            if course is not None and not course.empty:
                course_title = course['title']
                course_duration = parse_duration(course['duration'])
                st.write(f"Debug: {course_title} ({course_duration:.1f} hours)")

                unique_key = f"{skill}_{course_title.replace(' ', '_')}"
                if st.checkbox(f"{course_title} ({course_duration:.1f} hours)", key=unique_key):
                    selected_courses.append({"title": course_title, "duration": course_duration})

        st.write("Selected courses:", selected_courses)

        if st.button("Schedule Selected Courses"):
            if user_email and selected_courses:
                try:
                    service = get_user_calendar_service(user_email)
                    schedule_courses(service, selected_courses, study_time, available_hours, user_email)
                    st.success("Courses scheduled successfully!")
                except Exception as e:
                    st.error(f"An error occurred during scheduling: {e}")
            else:
                st.warning("Please select at least one course and provide your email.")

    if __name__ == "__main__":
        course_scheduler_ui()






elif st.session_state['current_page'] == "Mock Interview":
    st.title("🎙️ Mock Interview Page")
    st.write("This is the Mock Interview page.")
    if "interview_started" not in st.session_state:
        st.session_state.interview_started = True
    if "recording" not in st.session_state:
        st.session_state.recording = False
    if "filename" not in st.session_state:
        st.session_state.filename = "interview_response.wav"
    if "question_index" not in st.session_state:
        st.session_state.question_index = 0

    # Start Mock Interview
    if st.session_state.interview_started:
        fetched_api_key = ""
        genai.configure(api_key=fetched_api_key)
        model = genai.GenerativeModel("gemini-pro") 
        chat = model.start_chat()
        st.session_state.interview_started = True  # Set the session as active

        # Initialize Queue for audio recording
        q = queue.Queue()

        # Sample Rate and Duration
        sample_rate = 44100

        # Questions for the mock interview
        questions = [
            "Tell me about yourself.",
            "Why do you want this job?",
            "What are your strengths?",
            "What are your weaknesses?",
            "Where do you see yourself in 5 years?"
        ]

        # Display current question
        st.subheader(f"Question: {questions[st.session_state.question_index]}")

        # Recording function
        def record_audio():
            with sf.SoundFile(st.session_state.filename, mode="w", samplerate=sample_rate, channels=1) as file:
                with sd.InputStream(samplerate=sample_rate, channels=1, callback=audio_callback):
                    while st.session_state.recording:
                        file.write(q.get())

        # Audio callback
        def audio_callback(indata, frames, time, status):
            q.put(indata.copy())

        # Transcription
        def transcribe_audio():
            recognizer = sr.Recognizer()
            with sr.AudioFile(st.session_state.filename) as source:
                audio = recognizer.record(source)
                return recognizer.recognize_google(audio)

        # Feedback from OpenAI
        def get_feedback_response(transcript, question):
            prompt = f"""
            You are an interview coach. Here is the interview question: "{question}"
            The candidate's response was: "{transcript}"

            Provide constructive feedback on:
            1. How well the candidate addressed the question.
            2. Strengths in the response.
            3. Areas where the candidate could improve.
            4. Suggested keywords or phrases they could have included.
            """
            response = model.generate_content(prompt)
            return response.text
        
        col1, col2, col3, col4, col5, col6 = st.columns(6)

        with col1:
            button1 = st.button("Start Recording")

        with col2:
            button2 = st.button("Stop Recording")

        with col3:
            button3 = st.button("Play Recording")

        with col4:
            button4 = st.button("Get Feedback")

        with col5:
            button5 = st.button("Next Question")

        with col6:
            button6 = st.button("Exit Mock Interview")

        # Actions
        if button1:
            st.session_state.recording = True
            st.write("Recording started...")
            record_audio()

        if button2:
            st.session_state.recording = False
            st.write("Recording stopped.")

        if button3:
            data, fs = sf.read(st.session_state.filename, dtype="float32")
            sd.play(data, fs)
            sd.wait()

        if button4:
            st.write("Processing feedback...")
            transcript = transcribe_audio()
            feedback = get_feedback_response(transcript, questions[st.session_state.question_index])
            st.subheader("Feedback:")
            st.write(feedback)

        if button5:
            st.session_state.question_index = (st.session_state.question_index + 1) % len(questions)

        # Exit Mock Interview
        if button6:
            st.session_state.interview_started = False
            st.session_state.question_index = 0
            st.write("Thank you for participating in the Mock Interview!")

