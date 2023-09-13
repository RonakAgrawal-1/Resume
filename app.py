import streamlit as st
import os
import re
from PyPDF2 import PdfReader
from io import BytesIO
import docx2txt
from urllib.parse import urlparse
import requests
import pandas as pd
from skills_keywords import skills_keywords

# Function to extract the candidate's name from the resume
def extract_candidate_name(text):
    name_pattern = r'\b[A-Z][a-zA-Z]* [A-Z][a-zA-Z]*\b'
    candidate_name = re.search(name_pattern, text)
    return candidate_name.group() if candidate_name else "Name not found"

# Function to extract GitHub link from the resume text
def extract_github_link(text):
    github_keywords = ["github.com/", "https://github.com/"]
    for keyword in github_keywords:
        if keyword in text.lower():
            start_index = text.lower().index(keyword)
            end_index = text.find(" ", start_index)
            github_link = text[start_index:end_index].strip()
            return github_link
    return ""

# Function to extract the GitHub username from the URL
def extract_username_from_url(github_link):
    parsed_url = urlparse(github_link)
    if parsed_url.netloc == "github.com":
        path_parts = parsed_url.path.strip("/").split("/")
        if len(path_parts) >= 1:
            return path_parts[0]
    return None

# Function to fetch user repositories
def fetch_user_repositories(github_link_or_gmail, resume_text):
    username = extract_username_from_url(github_link_or_gmail)

    if username:
        github_user_url = f"https://api.github.com/users/{username}/repos"
        response = requests.get(github_user_url)
        if response.status_code == 200:
            return response.json()

    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b'
    gmail_match = re.search(email_pattern, resume_text)

    if gmail_match:
        gmail_address = gmail_match.group()
        github_search_url = f"https://api.github.com/search/users?q={gmail_address}"
        response = requests.get(github_search_url)

        if response.status_code == 200:
            search_results = response.json()

            if "items" in search_results:
                for item in search_results["items"]:
                    repos_url = item.get("repos_url")

                    if repos_url:
                        repos_response = requests.get(repos_url)

                        if repos_response.status_code == 200:
                            return repos_response.json()

    if not username:
        github_search_url = f"https://api.github.com/search/users?q={gmail_address.split('@')[0]}"
        response = requests.get(github_search_url)

        if response.status_code == 200:
            search_results = response.json()

            if "items" in search_results:
                for item in search_results["items"]:
                    repos_url = item.get("repos_url")

                    if repos_url:
                        repos_response = requests.get(repos_url)

                        if repos_response.status_code == 200:
                            return repos_response.json()

    return [{"name": "No repo found"}]

# Function to extract text from a PDF file
def extract_text_from_pdf(uploaded_file):
    try:
        resume_content = uploaded_file.read()
        pdf = PdfReader(BytesIO(resume_content))
        text = ""
        for page in pdf.pages:
            text += page.extract_text()
        return text
    except Exception as e:
        return {"error": str(e)}

# Function to extract text from a DOCX file
def extract_text_from_docx(uploaded_file):
    try:
        text = docx2txt.process(uploaded_file)
        return text
    except Exception as e:
        return {"error": str(e)}

# Function to extract skills from the resume text
def extract_candidate_skills(text):
    extracted_skills = []
    for skill in skills_keywords:
        pattern = rf'\b{re.escape(skill)}\b'
        if re.search(pattern, text, re.IGNORECASE):
            extracted_skills.append(skill.lower().capitalize())
    return extracted_skills

# Function to extract skills from the user-provided job description text
def extract_job_description_skills(job_description_text):
    extracted_skills = []
    for skill in skills_keywords:
        pattern = rf'\b{re.escape(skill)}\b'
        if re.search(pattern, job_description_text, re.IGNORECASE):
            extracted_skills.append(skill.lower().capitalize())
    return extracted_skills

# Function to calculate the matching score based on skills
def calculate_matching_score(candidate_skills, job_description_text):
    job_skills = extract_job_description_skills(job_description_text)
    common_skills = list(set(candidate_skills) & set(job_skills))

    if job_skills:
        score = len(common_skills) / len(job_skills)
    else:
        score = 0.0

    return score, common_skills

# Function to append new skill keyword to the skills_keywords.py file   
def append_skill_keyword(new_skill):
    try:
        with open("skills_keywords.py", "r") as file:
            lines = file.readlines()

        for i, line in enumerate(lines):
            if line.strip().startswith("skills_keywords = ["):
                before_bracket = line[:line.index("[") + 1]
                after_bracket = line[line.index("[") + 1:]

                if len(after_bracket.strip()) > 1:
                    lines[i] = before_bracket + after_bracket.rstrip() + f' "{new_skill}",\n'
                else:
                    lines[i] = before_bracket + f'"{new_skill}",\n'
                break

        with open("skills_keywords.py", "w") as file:
            file.writelines(lines)

        reload(skills_keywords)  # Reload the skills_keywords module to update the keyword list
        return True
    except Exception as e:
        return str(e)

def sort_candidates_by_matching_score(candidate_data):
    return sorted(candidate_data, key=lambda x: float(x["Matching Score"].strip('%')), reverse=True)

def create_matching_score_chart(score):
    percentage = int(score * 100)
    color = "green" if percentage >= 70 else "orange" if percentage >= 30 else "red"
    html_code = f"""
    <div class="chart">
        <div class="outer-circle">
            <div class="inner-circle" style="background: conic-gradient({color} {percentage}%, transparent 0%);"></div>
        </div>
        <div class="score" style="color: {color};">{percentage}%</div>
    </div>
    <style>
        .chart {{
            display: inline-block;
            width: 100px;
            height: 100px;
            position: relative;
            border: 2px solid #f5f5f5;
            border-radius: 50%;
        }}
        .outer-circle {{
            width: 100px;
            height: 100px;
            border-radius: 50%;
            background-color: #f5f5f5;
            position: relative;
        }}
        .inner-circle {{
            width: 100px;
            height: 100px;
            border-radius: 50%;
            position: absolute;
            clip-path: polygon(0 0, 100% 0, 100% 100%, 0 100%);
            animation: fillAnimation 2s linear forwards;
        }}
        .score {{
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            font-size: 20px;
            font-weight: bold;
        }}
        @keyframes fillAnimation {{
            to {{
                transform: rotate(360deg);
            }}
        }}
    </style>
    """
    return html_code

# Set Streamlit page title and icon
st.set_page_config(
    page_title="Resume and GitHub Analyzer",
    page_icon=":page_with_curl:"
)

# Introduction Section
st.title("Welcome to the Resume and GitHub Profile Analyzer!")

# Create a sidebar for inputs
st.sidebar.title("Resume and GitHub Analyzer")

# Upload Resume Section in Sidebar
st.sidebar.subheader("Step 1: Upload Resume Files")
uploaded_files = st.sidebar.file_uploader("Upload your resume files (PDF or DOC/DOCX)", accept_multiple_files=True)

# Enter Job Description Section in Sidebar
st.sidebar.subheader("Step 2: Enter Job Description")
job_description_text = st.sidebar.text_area("Enter the job description")

# ... (Your other setup code here)

# Display results for each candidate
if uploaded_files:
    # Create a DataFrame to store candidate information (name, matching score, details)
    candidate_data = []

    for uploaded_file in uploaded_files:
        # Extract text from the uploaded resume file
        if uploaded_file.type == "application/pdf":
            resume_text = extract_text_from_pdf(uploaded_file)
        elif uploaded_file.type in ["application/msword", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"]:
            resume_text = extract_text_from_docx(uploaded_file)
        else:
            st.warning(f"Skipping unsupported file: {uploaded_file.name}")
            continue

        # Calculate the matching score for the candidate
        candidate_skills = extract_candidate_skills(resume_text)
        score, common_skills = calculate_matching_score(candidate_skills, job_description_text)

        # Append candidate information to the DataFrame
        candidate_name = extract_candidate_name(resume_text)
        candidate_data.append({
            "Name": candidate_name,
            "Matching Score": f"{int(score * 100)}%",
            "Common Skills": common_skills,
            "Skills": candidate_skills,
            "Resume Text": resume_text
        })

    # Auto-sort candidate_data based on matching scores
    candidate_data = sorted(candidate_data, key=lambda x: float(x["Matching Score"].strip('%')), reverse=True)

    # Display candidates in a table-like dropdown

    # Create a list of candidate names and matching scores
    candidate_names = [candidate["Name"] for candidate in candidate_data]
    matching_scores = [candidate["Matching Score"] for candidate in candidate_data]

    # Create an empty list to store candidate details expanders
    candidate_expanders = []

    # Loop through the candidates and create expanders for each one
    for candidate_name, matching_score in zip(candidate_names, matching_scores):
        expander = st.expander(f"{candidate_name} (Matching Score: {matching_score})", expanded=False)
        candidate_expanders.append(expander)

    # Loop through sorted candidates and populate the expanders
    for candidate, expander in zip(candidate_data, candidate_expanders):
        with expander:
            # Display common skills, skills, GitHub repos, GitHub link, Gmail link, etc.
            st.subheader("Common Skills with Job Description")
            if candidate["Common Skills"]:
                for skill in candidate["Common Skills"]:
                    st.write(f"- {skill}")
            else:
                st.write("No common skills found between the job description and the candidate's skills.")

            st.subheader("Skills")
            if candidate["Skills"]:
                skills_text = ", ".join(candidate["Skills"])
            else:
                skills_text = "No skills found in the resume."
            st.write(skills_text)

            # Fetch and display GitHub repositories and other details if available
            st.subheader("GitHub Repositories and Technologies")
            github_link = extract_github_link(candidate["Resume Text"])
            if github_link:
                github_repositories = fetch_user_repositories(github_link, candidate["Resume Text"])
                if github_repositories:
                    repo_data = {
                        "Repository Name": [],
                        "Technologies Used": []
                    }
                    for repo in github_repositories:
                        repo_name = repo.get("name", "")
                        repo_language = repo.get("language", "")
                        if repo_name:
                            repo_data["Repository Name"].append(repo_name)
                        if repo_language:
                            repo_data["Technologies Used"].append(repo_language)

                    max_length = max(len(repo_data["Repository Name"]), len(repo_data["Technologies Used"]))
                    repo_data["Repository Name"] += [""] * (max_length - len(repo_data["Repository Name"]))
                    repo_data["Technologies Used"] += [""] * (max_length - len(repo_data["Technologies Used"]))

                    repo_df = pd.DataFrame(repo_data)
                    st.write(repo_df)
                else:
                    st.write(f"No repositories found for {github_link}.")
            else:
                st.write("No GitHub link found.")

            # Display Gmail address if available
            gmail_match = re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b', candidate["Resume Text"])
            if gmail_match:
                gmail_address = gmail_match.group()
                st.subheader("Gmail Address")
                st.write(gmail_address)
            else:
                st.write("No Gmail address found.")
            # Display matching score as a circular chart
            st.subheader("Matching Score")
            matching_score_chart = create_matching_score_chart(float(candidate["Matching Score"].strip('%')) / 100)
            st.markdown(matching_score_chart, unsafe_allow_html=True)
else:
    st.warning("Please upload resume files.")

# Create a Streamlit sidebar input for adding skills keywords
st.sidebar.title("Manage Skills Keywords")
new_skill = st.sidebar.text_input("Enter a new skill keyword")

# Button to add the new skill keyword
if st.sidebar.button("Add Skill Keyword", key="add_skill_button"):
    if append_skill_keyword(new_skill):
        st.success(f"Skill keyword '{new_skill}' added successfully!")
    else:
        st.warning("Failed to add the skill keyword. Please try again.")