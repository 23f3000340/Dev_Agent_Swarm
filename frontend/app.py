import streamlit as st
import streamlit as st
from github_utils import get_repo_files, get_file_content, commit_file_change, analyze_code

st.set_page_config(page_title="Code Vulnerability Dashboard", layout="wide", page_icon="🛡️")

st.sidebar.image("https://streamlit.io/images/brand/streamlit-logo-secondary-colormark-darktext.png", width=180)
st.sidebar.title("Navigation")
page = st.sidebar.radio("Go to", ["Dashboard", "Settings", "About"])

st.title("Code Vulnerability & Remediation Dashboard 🛡️")
st.markdown("""
This dashboard displays detected vulnerabilities, recommended code replacements, and allows you to apply fixes and commit changes directly to GitHub.
""")

# Session state initialization
if "findings" not in st.session_state:
    st.session_state["findings"] = []
if "repo_files" not in st.session_state:
    st.session_state["repo_files"] = []
if "selected_file" not in st.session_state:
    st.session_state["selected_file"] = None
if "github_token" not in st.session_state:
    st.session_state["github_token"] = ""
if "repo_name" not in st.session_state:
    st.session_state["repo_name"] = ""

if page == "Settings":
    st.subheader("Settings")
    github_token = st.text_input("GitHub Token", type="password", value=st.session_state["github_token"])
    repo_name = st.text_input("Repository Name", value=st.session_state["repo_name"])
    if st.button("Save Settings"):
        st.session_state["github_token"] = github_token
        st.session_state["repo_name"] = repo_name
        try:
            st.session_state["repo_files"] = get_repo_files(github_token, repo_name)
            st.success("Settings saved and repository files loaded!")
        except Exception as e:
            st.error(f"Error loading repository files: {e}")

if page == "Dashboard":
    st.subheader("Vulnerability Reports")
    if st.session_state["repo_files"]:
        selected_file = st.selectbox("Select a file to analyze", st.session_state["repo_files"])
        if st.button("Analyze File"):
            try:
                code = get_file_content(st.session_state["github_token"], st.session_state["repo_name"], selected_file)
                findings = analyze_code(code)
                st.session_state["findings"] = findings
                st.session_state["selected_file"] = selected_file
            except Exception as e:
                st.error(f"Error analyzing file: {e}")
    if st.session_state["findings"]:
        for idx, finding in enumerate(st.session_state["findings"]):
            with st.expander(f"{finding['severity']} | {st.session_state['selected_file']} (Line {finding['line']})"):
                st.write(f"**Description:** {finding['description']}")
                st.code(finding['bad_code'], language="python")
                st.write("**Recommended Replacement:**")
                st.code(finding['recommended_code'], language="python")
                if st.button(f"Apply & Commit Fix for Line {finding['line']}", key=f"commit_{idx}"):
                    try:
                        code = get_file_content(st.session_state["github_token"], st.session_state["repo_name"], st.session_state["selected_file"])
                        new_code = code.replace(finding['bad_code'], finding['recommended_code'])
                        commit_file_change(st.session_state["github_token"], st.session_state["repo_name"], st.session_state["selected_file"], new_code, f"Fix: {finding['description']}")
                        st.success("Fix applied and committed to GitHub!")
                    except Exception as e:
                        st.error(f"Error committing fix: {e}")
    else:
        st.info("No findings yet. Please analyze a file.")

if page == "About":
    st.subheader("About This Dashboard")
    st.markdown("""
    **DevAgent Swarm** - AI-powered code review and remediation tool.\nBuilt with Streamlit for rapid, interactive reporting and direct GitHub integration.
    """)
    st.write("Contact: support@devagent-swarm.com")
    st.subheader("Settings")
    st.write("Configure GitHub integration, repository, and notification preferences.")
    st.text_input("GitHub Token", type="password")
    st.text_input("Repository Name", value="23f3000340/covid-xray-classifier")
    st.button("Save Settings")

# --- About Page ---
if page == "About":
    st.subheader("About This Dashboard")
    st.markdown("""
    **DevAgent Swarm** - AI-powered code review and remediation tool.\nBuilt with Streamlit for rapid, interactive reporting and direct GitHub integration.
    """)
    st.write("Contact: support@devagent-swarm.com")
