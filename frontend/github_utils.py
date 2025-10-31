import requests
from github import Github
from typing import List, Dict

def get_repo_files(token: str, repo_name: str) -> List[str]:
    g = Github(token)
    repo = g.get_repo(repo_name)
    return [f.path for f in repo.get_contents("") if f.type == "file"]

def get_file_content(token: str, repo_name: str, file_path: str) -> str:
    g = Github(token)
    repo = g.get_repo(repo_name)
    file_content = repo.get_contents(file_path)
    return file_content.decoded_content.decode()

def commit_file_change(token: str, repo_name: str, file_path: str, new_content: str, commit_message: str) -> str:
    g = Github(token)
    repo = g.get_repo(repo_name)
    file = repo.get_contents(file_path)
    repo.update_file(file_path, commit_message, new_content, file.sha)
    return "Committed successfully"

# Dummy analyzer for demonstration
# Replace with actual analysis logic or API call

def analyze_code(code: str) -> List[Dict]:
    # Example: Detect hardcoded password
    findings = []
    if "password = '" in code:
        findings.append({
            "description": "Hardcoded credentials",
            "bad_code": "password = '1234'",
            "recommended_code": "import os\npassword = os.getenv('APP_PASSWORD')",
            "line": 1,
            "severity": "CRITICAL"
        })
    return findings
