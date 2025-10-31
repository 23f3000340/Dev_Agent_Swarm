import streamlit as st
import datetime
from github import Github

# --- Branding & Layout ---
st.set_page_config(page_title="DevAgent Swarm Pro Dashboard", layout="wide", page_icon="🛡️")
st.markdown("""
    <style>
        .main {background-color: #f7f9fa;}
        .stButton>button {background-color: #0072ff; color: white; font-weight: bold;}
        .stMetric {font-size: 1.2em;}
        .css-1v0mbdj {background: #fff; border-radius: 10px;}
    </style>
    """, unsafe_allow_html=True)
st.image("https://streamlit.io/images/brand/streamlit-logo-secondary-colormark-darktext.png", width=180)
st.title("DevAgent Swarm: AI Code Review & Auto-Fix Dashboard 🛡️")

# --- Sidebar: Authentication & Repo Selection ---
st.sidebar.header("Connect to GitHub Repository")
github_token = st.sidebar.text_input("GitHub Token", type="password")
repo_url = st.sidebar.text_input("GitHub Repo (owner/repo)", value="23f3000340/covid-xray-classifier")

if st.sidebar.button("Connect & Analyze"):
    try:
        g = Github(github_token)
        repo = g.get_repo(repo_url)
        files = [f.path for f in repo.get_contents("") if f.type == "file"]
        st.session_state["files"] = files
        st.session_state["repo"] = repo
        st.session_state["last_scan"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        st.success(f"Connected to {repo_url} and loaded files.")
    except Exception as e:
        st.error(f"Error: {e}")

# --- Dashboard Overview ---
st.subheader("Dashboard Overview")
col1, col2, col3 = st.columns(3)
col1.metric("Files Analyzed", str(len(st.session_state.get("files", []))))
col2.metric("Vulnerabilities Found", "-")
col3.metric("Last Scan", st.session_state.get("last_scan", "Never"))

# --- File Selection & Analysis ---
if "files" in st.session_state and st.session_state["files"]:
    st.subheader("Select a file to analyze")
    selected_file = st.selectbox("Repository Files", st.session_state["files"])
    if st.button("Analyze File"):
        try:
            file_content = st.session_state["repo"].get_contents(selected_file).decoded_content.decode()
            # TODO: Replace with your agent's analysis logic
            findings = []
            if "password = '" in file_content:
                findings.append({
                    "line": 1,
                    "severity": "CRITICAL",
                    "description": "Hardcoded credentials",
                    "bad_code": "password = '1234'",
                    "recommended_code": "import os\npassword = os.getenv('APP_PASSWORD')"
                })
            st.session_state["findings"] = findings
            st.session_state["selected_file"] = selected_file
            st.success(f"Analysis complete for {selected_file}.")
        except Exception as e:
            st.error(f"Error analyzing file: {e}")

# --- Findings Table ---
if "findings" in st.session_state and st.session_state["findings"]:
    st.subheader("Findings for " + st.session_state["selected_file"])
    for idx, f in enumerate(st.session_state["findings"]):
        color = {"CRITICAL": "#ff4b4b", "HIGH": "#ff9800", "MEDIUM": "#ffd600", "LOW": "#8bc34a"}.get(f["severity"], "#fff")
        with st.expander(f"{f['severity']} | Line {f['line']}"):
            st.markdown(f"<span style='color:{color};font-weight:bold;'>Severity: {f['severity']}</span>", unsafe_allow_html=True)
            st.write(f"**Description:** {f['description']}")
            st.code(f["bad_code"], language="python")
            st.write("**Recommended Replacement:**")
            st.code(f["recommended_code"], language="python")
            commit_msg = st.text_input(f"Commit message for fix {idx}", value=f"Fix: {f['description']}")
            if st.button(f"Apply & Commit Fix for Line {f['line']}", key=f"commit_{idx}"):
                try:
                    file_content = st.session_state["repo"].get_contents(st.session_state["selected_file"]).decoded_content.decode()
                    new_content = file_content.replace(f["bad_code"], f["recommended_code"])
                    st.session_state["repo"].update_file(
                        st.session_state["selected_file"],
                        commit_msg,
                        new_content,
                        st.session_state["repo"].get_contents(st.session_state["selected_file"]).sha
                    )
                    st.success("Fix applied and committed to GitHub!")
                except Exception as e:
                    st.error(f"Error committing fix: {e}")

# --- Visualization & Insights ---
st.subheader("Insights & Charts")
st.write("(Add pie/bar charts of issue types/severity here)")
# TODO: Integrate matplotlib/plotly for charts

# --- Notifications & Feedback ---
st.subheader("Feedback & Report")
if st.button("Download Report (Markdown)"):
    st.info("Report downloaded (demo)")
with st.form("feedback_form"):
    feedback = st.text_area("Your feedback")
    submitted = st.form_submit_button("Submit Feedback")
    if submitted:
        st.success("Thank you for your feedback!")

st.markdown("---")
st.markdown("_Built by DevAgent Swarm for hackathons & beyond!_")
