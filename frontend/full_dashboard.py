import streamlit as st
import datetime
from github import Github
import importlib.util
import sys
import os

# --- Branding & Layout ---
st.set_page_config(page_title="DevAgent Swarm Full Dashboard", layout="wide", page_icon="🛡️")
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
repo_options = []
if github_token:
    try:
        g = Github(github_token)
        user = g.get_user()
        repo_options = [repo.full_name for repo in user.get_repos()]
    except Exception as e:
        st.sidebar.error(f"Error fetching repos: {e}")
if repo_options:
    repo_url = st.sidebar.selectbox("Select GitHub Repo", repo_options)
else:
    repo_url = st.sidebar.text_input("GitHub Repo (owner/repo)", value="")
issue_number = st.sidebar.text_input("GitHub Issue Number (optional)")

if st.sidebar.button("Connect & Load Files"):
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

# --- File Selection ---
if "files" in st.session_state and st.session_state["files"]:
    st.subheader("Select files to analyze")
    selected_files = st.multiselect("Repository Files", st.session_state["files"], default=st.session_state["files"][:1])
    if st.button("Analyze Selected Files"):
        findings_all = []
        try:
            # Dynamically import your agent using absolute path
            backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'github_issue_commenter.py'))
            spec = importlib.util.spec_from_file_location("github_issue_commenter", backend_path)
            github_issue_commenter = importlib.util.module_from_spec(spec)
            sys.modules["github_issue_commenter"] = github_issue_commenter
            spec.loader.exec_module(github_issue_commenter)
            for file_path in selected_files:
                file_content = st.session_state["repo"].get_contents(file_path).decoded_content.decode()
                findings = github_issue_commenter.analyze_file(file_content, file_path)
                for f in findings:
                    f["file"] = file_path
                findings_all.extend(findings)
            st.session_state["findings"] = findings_all
            st.success(f"Analysis complete for {len(selected_files)} file(s).")
        except Exception as e:
            st.error(f"Error analyzing files: {e}")

# --- Findings Table ---
if "findings" in st.session_state and st.session_state["findings"]:
    st.subheader("Findings")
    for idx, f in enumerate(st.session_state["findings"]):
        color = {"CRITICAL": "#ff4b4b", "HIGH": "#ff9800", "MEDIUM": "#ffd600", "LOW": "#8bc34a"}.get(f.get("severity", ""), "#fff")
        with st.expander(f"{f.get('severity', '')} | {f.get('file', '')} (Line {f.get('line', '-')})"):
            st.markdown(f"<span style='color:{color};font-weight:bold;'>Severity: {f.get('severity', '')}</span>", unsafe_allow_html=True)
            st.write(f"**Description:** {f.get('description', '')}")
            st.write(f"**Why Harmful:** {f.get('why_harmful', '')}")
            st.write(f"**Best Practice:** {f.get('best_practice', '')}")
            st.write("**Previous Code:**")
            st.code(f.get("bad_code", "") or f.get("actual_code", ""), language="python")
            st.write("**Recommended Replacement:**")
            st.code(f.get("recommended_code", "") or f.get("fixed_code", ""), language="python")
            commit_msg = st.text_input(f"Commit message for fix {idx}", value=f"Fix: {f.get('description', '')}")
            recommended_code = f.get("recommended_code", "") or f.get("fixed_code", "")
            previous_code = f.get("bad_code", "") or f.get("actual_code", "")
            if recommended_code:
                if st.button(f"Apply & Commit Fix for {f.get('file', '')} Line {f.get('line', '-')}", key=f"commit_{idx}"):
                    try:
                        file_content = st.session_state["repo"].get_contents(f["file"]).decoded_content.decode()
                        new_content = file_content.replace(previous_code, recommended_code)
                        st.session_state["repo"].update_file(
                            f["file"],
                            commit_msg,
                            new_content,
                            st.session_state["repo"].get_contents(f["file"]).sha
                        )
                        st.success("Fix applied and committed to GitHub!")
                    except Exception as e:
                        st.error(f"Error committing fix: {e}")
            else:
                st.warning("No recommended code available for this finding. Cannot commit fix.")
            if issue_number and st.button(f"Comment on Issue #{issue_number}", key=f"comment_{idx}"):
                try:
                    # Call your agent's comment function
                    backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'github_issue_commenter.py'))
                    spec = importlib.util.spec_from_file_location("github_issue_commenter", backend_path)
                    github_issue_commenter = importlib.util.module_from_spec(spec)
                    sys.modules["github_issue_commenter"] = github_issue_commenter
                    spec.loader.exec_module(github_issue_commenter)
                    comment_body = github_issue_commenter.make_markdown_comment([f], 1)
                    repo = st.session_state["repo"]
                    issue = repo.get_issue(int(issue_number))
                    issue.create_comment(comment_body)
                    st.success(f"Commented on issue #{issue_number}!")
                except Exception as e:
                    st.error(f"Error commenting on issue: {e}")

# --- Visualization & Insights ---
st.subheader("Insights & Charts")
st.write("(Add pie/bar charts of issue types/severity here)")
# TODO: Integrate matplotlib/plotly for charts

# --- Notifications & Feedback ---
st.subheader("Feedback & Report")
if st.button("Download Report (Markdown)"):
    try:
        backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'github_issue_commenter.py'))
        spec = importlib.util.spec_from_file_location("github_issue_commenter", backend_path)
        github_issue_commenter = importlib.util.module_from_spec(spec)
        sys.modules["github_issue_commenter"] = github_issue_commenter
        spec.loader.exec_module(github_issue_commenter)
        report = github_issue_commenter.make_markdown_comment(st.session_state["findings"], len(st.session_state["findings"]))
        st.download_button("Download Report", report, file_name="report.md")
    except Exception as e:
        st.error(f"Error generating report: {e}")
with st.form("feedback_form"):
    feedback = st.text_area("Your feedback")
    submitted = st.form_submit_button("Submit Feedback")
    if submitted:
        st.success("Thank you for your feedback!")

st.markdown("---")
st.markdown("_Built by DevAgent Swarm for hackathons & beyond!_")
