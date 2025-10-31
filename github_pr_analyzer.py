import os
import sys
import json
import time
import logging
import requests
from datetime import datetime
from dotenv import load_dotenv
from github import Github, Auth
import boto3

# --- Logging setup ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("DevAgentSwarm")

# --- Load environment variables ---
load_dotenv()
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
BEDROCK_MODEL_ID = os.getenv("BEDROCK_MODEL_ID", "amazon.nova-pro-v1:0")

# Supported file extensions
SUPPORTED_EXTS = {".py", ".js", ".ts", ".java", ".cpp", ".c", ".go", ".rs", ".rb", ".jsx", ".tsx"}

# --- Helper functions ---
def get_bedrock_client():
    return boto3.client(
        "bedrock-runtime",
        region_name=AWS_REGION,
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY
    )

def call_bedrock_agent(agent_type, code, file_name):
    """Call Bedrock LLM for analysis. agent_type: 'security', 'quality', 'testing'"""
    prompt_map = {
        "security": (
            f"Analyze this code for SECURITY VULNERABILITIES ONLY. "
            f"File: {file_name}\n{code[:2000]}\n"
            "Return ONLY a JSON array of objects: [{ 'severity': 'CRITICAL', 'line': 5, 'description': 'SQL injection', 'why': 'Allows attackers to execute arbitrary SQL', 'suggestion': 'Use parameterized queries', 'code_bad': '...', 'code_good': '...' }]"
            "Be thorough and find all security issues like SQL injection, hardcoded secrets, authentication bypass, etc."
        ),
        "quality": (
            f"Analyze this code for CODE QUALITY, DESIGN, and PERFORMANCE ISSUES ONLY. "
            f"File: {file_name}\n{code[:2000]}\n"
            "Return ONLY a JSON array of objects: [{ 'severity': 'HIGH', 'line': 17, 'description': 'Race condition', 'why': 'Can cause inconsistent state', 'suggestion': 'Use threading.Lock()', 'code_bad': '...', 'code_good': '...' }]"
            "Be thorough and find all issues like race conditions, memory leaks, N+1 queries, high complexity, code duplication, etc."
        ),
        "testing": (
            f"Analyze this code for MISSING TEST COVERAGE and recommend tests. "
            f"File: {file_name}\n{code[:2000]}\n"
            "Return ONLY a JSON array of objects: [{ 'type': 'unit', 'description': 'recommendation', 'why': '...' }]"
            "Recommend specific unit, integration, and edge case tests."
        )
    }
    body = {
        "inferenceConfig": {
            "maxTokens": 1024,
            "temperature": 0.7
        },
        "messages": [{
            "role": "user",
            "content": [{"text": prompt_map[agent_type]}]
        }]
    }
    try:
        client = get_bedrock_client()
        response = client.invoke_model(
            modelId=BEDROCK_MODEL_ID,
            body=json.dumps(body)
        )
        result = json.loads(response["body"].read())
        if "output" in result:
            text = result["output"]["message"]["content"][0]["text"].strip()
        else:
            text = result.get("content", [{}])[0].get("text", "").strip()
        json_start = text.find("[")
        json_end = text.rfind("]") + 1
        if json_start >= 0 and json_end > json_start:
            return json.loads(text[json_start:json_end])
    except Exception as e:
        logger.error(f"Bedrock {agent_type} agent error for {file_name}: {e}")
    return []

def make_markdown_comment(all_findings, file_count):
    now = datetime.utcnow().isoformat() + "Z"
    lines = [
        "## 🤖 Security/Quality/Test Review — DevAgent Swarm",
        f"**Analysis Time:** {now}",
        f"**Files Analyzed:** {file_count}",
        "",
        "### 🔒 Security Issues"
    ]
    crit, high, med, low = 0, 0, 0, 0
    for finding in all_findings:
        sev = finding.get("severity", "LOW").upper()
        line = finding.get("line", "?")
        desc = finding.get("description", "")
        why = finding.get("why", "")
        suggestion = finding.get("suggestion", "")
        code_bad = finding.get("code_bad", None)
        code_good = finding.get("code_good", None)
        emoji = "🔴" if sev == "CRITICAL" else "🟠" if sev == "HIGH" else "🟡" if sev == "MEDIUM" else "🟢"
        if sev == "CRITICAL": crit += 1
        if sev == "HIGH": high += 1
        if sev == "MEDIUM": med += 1
        if sev == "LOW": low += 1
        lines.append(f"{emoji} **{sev}** (Line {line}): {desc}")
        if why:
            lines.append(f"**Why is this harmful?**  \n{why}")
        if suggestion:
            lines.append(f"**Suggested Replacement:**  \n{suggestion}")
        if code_bad:
            lines.append(f"**Bad:**  \n```python\n{code_bad}\n```")
        if code_good:
            lines.append(f"**Good:**  \n```python\n{code_good}\n```")
        lines.append("")
    lines.append("---")
    lines.append(f"**Summary:**  \nAnalyzed {file_count} file(s) | {crit} critical | {high} high | {med} medium | {low} low  \n_This security and quality check was generated by DevAgent Swarm 🤖_")
    return "\n".join(lines)

def post_comment(pr, body):
    try:
        pr.create_issue_comment(body)
        logger.info(f"Posted comment to PR #{pr.number}")
    except Exception as e:
        logger.error(f"Error posting comment to PR #{pr.number}: {e}")

def get_repo_name(arg):
    if arg.startswith("https://github.com/"):
        parts = arg.rstrip("/").split("/")
        if len(parts) >= 5:
            return f"{parts[3]}/{parts[4]}"
    return arg

def main():
    repo_arg = None
    state = "open"
    if len(sys.argv) > 1:
        repo_arg = sys.argv[1]
        if len(sys.argv) > 2:
            state = sys.argv[2]
    else:
        repo_arg = os.getenv("GITHUB_REPO")
        if not repo_arg:
            logger.error("Usage: python github_pr_analyzer.py owner/repo [open|closed|all]")
            sys.exit(1)
    repo_name = get_repo_name(repo_arg)
    if state not in {"open", "closed", "all"}:
        logger.warning(f"Unknown PR state '{state}', defaulting to 'open'.")
        state = "open"

    if not GITHUB_TOKEN:
        logger.error("Missing GITHUB_TOKEN in .env")
        sys.exit(1)
    if not AWS_ACCESS_KEY_ID or not AWS_SECRET_ACCESS_KEY:
        logger.error("Missing AWS credentials in .env")
        sys.exit(1)

    try:
        gh = Github(auth=Auth.Token(GITHUB_TOKEN))
        repo = gh.get_repo(repo_name)
    except Exception as e:
        logger.error(f"Error accessing repo '{repo_name}': {e}")
        sys.exit(1)

    try:
        prs = repo.get_pulls(state=state)
    except Exception as e:
        logger.error(f"Error fetching PRs: {e}")
        sys.exit(1)

    for pr in prs:
        logger.info(f"Analyzing PR #{pr.number}: {pr.title}")
        files = pr.get_files()
        file_count = 0
        all_findings = []
        for f in files:
            ext = os.path.splitext(f.filename)[1]
            if ext not in SUPPORTED_EXTS:
                continue
            file_count += 1
            try:
                code = requests.get(f.raw_url).text
            except Exception as e:
                logger.error(f"Error fetching file {f.filename}: {e}")
                continue
            # Aggregate all agent findings for this file
            for agent in ["security", "quality", "testing"]:
                findings = call_bedrock_agent(agent, code, f.filename)
                for finding in findings:
                    finding["file"] = f.filename
                    all_findings.append(finding)
            time.sleep(1)  # Rate limit
        if all_findings:
            comment = make_markdown_comment(all_findings, file_count)
            post_comment(pr, comment)
        else:
            logger.info(f"No issues found for PR #{pr.number}; skipping comment.")
        time.sleep(2)  # Rate limit

if __name__ == "__main__":
    main()
