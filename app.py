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
    # Create a DataFrame to store candidate information (name, matching score)
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
        candidate_data.append({"Name": candidate_name, "Matching Score": f"{int(score * 100)}%"})

        # Create an expandable section for the candidate details
        with st.expander(f"Details for {candidate_name} (Matching Score: {int(score * 100)}%)"):
            # Display common skills, all skills, GitHub repos, GitHub link, Gmail link, etc.
            st.subheader("Common Skills with Job Description")
            if common_skills:
                for skill in common_skills:
                    st.write(f"- {skill}")
            else:
                st.write("No common skills found between the job description and the candidate's skills.")

            st.subheader("Candidate Skills")
            extracted_skills = extract_candidate_skills(resume_text)
            if extracted_skills:
                skills_text = ", ".join(extracted_skills)
            else:
                skills_text = "No skills found in the resume."
            st.write(skills_text)

            # Fetch and display GitHub repositories and other details if available
            st.subheader("GitHub Repositories and Technologies")
            github_link = extract_github_link(resume_text)
            if github_link:
                github_repositories = fetch_user_repositories(github_link, resume_text)
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
            email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b'
            gmail_match = re.search(email_pattern, resume_text)
            if gmail_match:
                gmail_address = gmail_match.group()
                st.subheader("Gmail Address")
                st.write(gmail_address)
            else:
                st.write("No Gmail address found.")
else:
    st.warning("Please upload resume files.")

# Create a Streamlit sidebar input for adding skills keywords
st.sidebar.title("Manage Skills Keywords")
new_skill = st.sidebar.text_input("Enter a new skill keyword")

# Button to add the new skill keyword
if st.sidebar.button("Add Skill Keyword"):
    if append_skill_keyword(new_skill):
        st.success(f"Skill keyword '{new_skill}' added successfully!")
    else:
        st.warning("Failed to add the skill keyword. Please try again.")

