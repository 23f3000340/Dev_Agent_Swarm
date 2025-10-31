import os
import sys
import json
import logging
import requests
from dotenv import load_dotenv
from github import Github, Auth
import boto3

# --- Logging setup ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("DevAgentSwarmIssueCommenter")


load_dotenv()
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
BEDROCK_MODEL_ID = os.getenv("BEDROCK_MODEL_ID", "amazon.nova-pro-v1:0")

SUPPORTED_EXTS = {".py", ".js", ".ts", ".java", ".cpp", ".c", ".go", ".rs", ".rb", ".jsx", ".tsx"}

def get_bedrock_client():
    return boto3.client(
        "bedrock-runtime",
        region_name=AWS_REGION,
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY
    )

def validate_finding(finding, code_lines, chunk_start_line):
    """
    Validate that a finding actually corresponds to real code at the reported line.
    Returns True if the finding is valid, False otherwise.
    """
    if "line" not in finding or not isinstance(finding["line"], int):
        return False

    line_idx = finding["line"] - 1  # Convert to 0-based index
    if line_idx < 0 or line_idx >= len(code_lines):
        return False

    # Check if the reported line contains relevant code for the finding type
    line_content = code_lines[line_idx].strip().lower()

    # Security validations
    if finding.get("type") == "security":
        issue_desc = finding.get("description", "").lower()
        if "sql injection" in issue_desc and ("select" not in line_content and "insert" not in line_content and "update" not in line_content and "delete" not in line_content):
            return False
        if "file not being closed" in issue_desc and "open(" not in line_content:
            return False
        if "race condition" in issue_desc and ("+=" not in line_content and "global" not in line_content):
            return False
        if "hardcoded secrets" in issue_desc and not any(keyword in line_content for keyword in ["password", "secret", "key", "token"]):
            return False

    # Quality validations
    elif finding.get("type") == "quality":
        issue_desc = finding.get("description", "").lower()
        if "magic numbers" in issue_desc and not any(char.isdigit() for char in line_content):
            return False
        if "code duplication" in issue_desc and not any(keyword in line_content for keyword in ["def ", "class ", "="]):
            return False
        if "high complexity" in issue_desc and "if " not in line_content:
            return False

    return True

def call_bedrock_agent(agent_type, code, file_name):
    """
    Enhanced agent function with validation and improved prompts for accuracy.
    """
    # Split code into lines for accurate line number tracking
    code_lines = code.splitlines()
    max_lines_per_chunk = 150  # Smaller chunks for better context

    all_findings = []
    current_line_offset = 0

    for chunk_idx in range(0, len(code_lines), max_lines_per_chunk):
        chunk_lines = code_lines[chunk_idx:chunk_idx + max_lines_per_chunk]
        chunk_code = '\n'.join(chunk_lines)

        # Create more specific, validation-focused prompts
        prompt_map = {
            "security": f"""Analyze this Python code chunk for REAL security vulnerabilities. Be precise and only report issues that actually exist in the code shown.

REQUIREMENTS:
- Only report vulnerabilities that are clearly present in the provided code
- Specify the EXACT line number where the vulnerable code appears
- Include the actual problematic code snippet in your response
- Focus on: SQL injection, XSS, authentication bypass, insecure file handling, race conditions, hardcoded secrets

Return ONLY a JSON array. Each finding must have: severity, line (exact number), description, why_harmful, best_practice, actual_code, fixed_code, remediation_steps, references.

If no real security issues exist in this code, return [].

Code chunk (lines {current_line_offset + 1}-{current_line_offset + len(chunk_lines)}):
{chunk_code}""",

            "quality": f"""Analyze this Python code for REAL quality and maintainability issues. Only report actual problems.

REQUIREMENTS:
- Only report issues that genuinely affect code quality
- Specify exact line numbers where issues occur
- Focus on: code duplication, excessive complexity, poor naming, resource leaks, deprecated usage
- Include actual code examples from the chunk

Return ONLY a JSON array with: severity, line, description, why_harmful, best_practice, actual_code, fixed_code, remediation_steps, references.

If no real quality issues exist, return [].

Code chunk (lines {current_line_offset + 1}-{current_line_offset + len(chunk_lines)}):
{chunk_code}""",

            "testing": f"""Recommend specific, actionable tests for this Python code. Focus on real testing gaps.

REQUIREMENTS:
- Only suggest tests for functions/methods that actually exist in the code
- Include specific test scenarios based on the code logic
- Focus on: edge cases, error conditions, security scenarios

Return ONLY a JSON array with: test_type, description, why_important, test_code, assertions.

If no meaningful tests needed, return [].

Code chunk (lines {current_line_offset + 1}-{current_line_offset + len(chunk_lines)}):
{chunk_code}"""
        }

        body = {
            "inferenceConfig": {
                "maxTokens": 4096,
                "temperature": 0.05  # Even lower temperature for precision
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

            logger.info(f"LLM response for {agent_type} chunk {chunk_idx // max_lines_per_chunk + 1}: {text[:300]}...")

            # Extract and validate JSON
            json_start = text.find("[")
            json_end = text.rfind("]") + 1
            if json_start >= 0 and json_end > json_start:
                chunk_findings = json.loads(text[json_start:json_end])

                # Validate and adjust each finding
                validated_findings = []
                for finding in chunk_findings:
                    # Adjust line number to global file position
                    if "line" in finding and isinstance(finding["line"], int):
                        finding["line"] += current_line_offset

                    # Validate the finding against actual code
                    if validate_finding(finding, code_lines, current_line_offset):
                        finding["type"] = agent_type
                        validated_findings.append(finding)
                    else:
                        logger.debug(f"Filtered out invalid finding: {finding.get('description', 'Unknown')}")

                all_findings.extend(validated_findings)
                logger.info(f"Validated {len(validated_findings)}/{len(chunk_findings)} findings for chunk {chunk_idx // max_lines_per_chunk + 1}")

        except Exception as e:
            logger.error(f"Bedrock {agent_type} agent error for {file_name} chunk {chunk_idx // max_lines_per_chunk + 1}: {e}")

        current_line_offset += len(chunk_lines)

    return all_findings

def safe_stringify(obj):
    """
    Safely convert any object to a string, handling lists, dicts, and other types.
    """
    if isinstance(obj, str):
        return obj
    elif isinstance(obj, list):
        return '\n'.join([safe_stringify(item) for item in obj])
    elif isinstance(obj, dict):
        return json.dumps(obj, indent=2)
    else:
        return str(obj)

def make_markdown_comment(all_findings, file_count):
    """
    Generate a comprehensive markdown comment from analysis findings.

    Args:
        all_findings: List of validated findings from all agents
        file_count: Number of files that were analyzed

    Returns:
        str: Formatted markdown comment for GitHub issue
    """
    # Initialize the comment header
    lines = [
        "## 🤖 Security/Quality/Test Review — DevAgent Swarm",
        f"**Files Analyzed:** {file_count}",
        ""
    ]

    # Count findings by severity for summary
    crit, high, med, low = 0, 0, 0, 0
    grouped_findings = {"security": [], "quality": [], "testing": []}

    # Group findings by type and count severities
    for finding in all_findings:
        agent_type = finding.get("type", "security")
        grouped_findings[agent_type].append(finding)
        sev = finding.get("severity", "LOW").upper()
        if sev == "CRITICAL": crit += 1
        elif sev == "HIGH": high += 1
        elif sev == "MEDIUM": med += 1
        elif sev == "LOW": low += 1

    # Process each finding type section
    for agent_type, findings in grouped_findings.items():
        if not findings:
            continue

        # Add section header based on agent type
        if agent_type == "security":
            lines.append("### 🔒 Security Issues")
        elif agent_type == "quality":
            lines.append("### 🛠️ Quality Issues")
        elif agent_type == "testing":
            lines.append("### 🧪 Testing Recommendations")
        lines.append("")

        # Process each finding in this section
        for finding in findings:
            file_name = finding.get("file", "")
            line = finding.get("line", "?")
            desc = finding.get("description", "")
            # Handle both old and new field names for backward compatibility
            why = finding.get("why") or finding.get("why_harmful", "")
            best_practice = finding.get("best_practice", "")
            suggestion = finding.get("suggestion", "")
            # Handle both old and new field names for code examples
            code_bad = finding.get("code_bad") or finding.get("actual_code", "")
            code_good = finding.get("code_good") or finding.get("fixed_code", "")
            remediation_steps = finding.get("remediation_steps", "")
            references = finding.get("references", "")
            sev = finding.get("severity", "LOW").upper()

            # Severity emoji for visual impact
            emoji = "🔴" if sev == "CRITICAL" else "🟠" if sev == "HIGH" else "🟡" if sev == "MEDIUM" else "🟢"

            # Build the finding entry
            lines.append(f"**File:** {file_name}")
            lines.append(f"**Line:** {line}")
            lines.append(f"**Severity:** {sev} {emoji}")
            lines.append(f"**Issue:** {desc}")
            lines.append("")

            # Add explanation if available
            if why:
                lines.append(f"**Why is this harmful?**")
                # Handle both string and list formats
                if isinstance(why, list):
                    lines.extend([str(item) for item in why])
                else:
                    lines.append(str(why))
                lines.append("")

            # Add best practice guidance
            if best_practice:
                lines.append(f"**Best Practice:**")
                # Handle both string and list formats
                if isinstance(best_practice, list):
                    lines.extend([str(item) for item in best_practice])
                else:
                    lines.append(str(best_practice))
                lines.append("")

            # Add suggestion if available
            if suggestion:
                lines.append(f"**Suggested Fix:**")
                # Handle both string and list formats
                if isinstance(suggestion, list):
                    lines.extend([str(item) for item in suggestion])
                else:
                    lines.append(str(suggestion))
                lines.append("")

            # Add code examples if provided
            if code_bad or code_good:
                lines.append("**Code Example:**")
                if code_bad:
                    lines.append("**❌ Bad:**")
                    lines.append("```python")
                    # Ensure code_bad is a string
                    if isinstance(code_bad, list):
                        lines.extend(code_bad)
                    else:
                        lines.append(str(code_bad))
                    lines.append("```")
                if code_good:
                    lines.append("**✅ Good:**")
                    lines.append("```python")
                    # Ensure code_good is a string
                    if isinstance(code_good, list):
                        lines.extend(code_good)
                    else:
                        lines.append(str(code_good))
                    lines.append("```")
                lines.append("")

            # Add remediation steps
            if remediation_steps:
                lines.append("**Remediation Steps:**")
                # Handle both string and list formats
                if isinstance(remediation_steps, list):
                    lines.extend(remediation_steps)
                else:
                    lines.append(str(remediation_steps))
                lines.append("")

            # Add references if available
            if references:
                lines.append("**References:**")
                lines.append(references)
                lines.append("")

            # Separator between findings
            lines.append("---")
            lines.append("")

    # Add summary section
    lines.append("**Summary:**")
    lines.append(f"Analyzed {file_count} file(s) | {crit} critical | {high} high | {med} medium | {low} low")
    lines.append("")
    lines.append("_This analysis was generated by DevAgent Swarm 🤖 - AI-powered code review_")

    # Ensure all items in lines are strings before joining
    flat_lines = []
    for item in lines:
        if isinstance(item, list):
            flat_lines.extend([str(subitem) for subitem in item])
        else:
            flat_lines.append(str(item))
    return "\n".join(flat_lines)

def get_repo_files(repo, path=""):
    """Recursively get all files from the repository."""
    contents = repo.get_contents(path)
    files = []
    for content in contents:
        if content.type == "file":
            files.append(content)
        elif content.type == "dir":
            files.extend(get_repo_files(repo, content.path))
    return files


# --- Frontend Integration Functions ---
def analyze_file(code, file_name):
    """
    Analyze a single file and return findings (security, quality, testing).
    """
    all_findings = []
    for agent in ["security", "quality", "testing"]:
        findings = call_bedrock_agent(agent, code, file_name)
        for finding in findings:
            finding["file"] = file_name
            finding["type"] = agent
            all_findings.append(finding)
    return all_findings

def analyze_files(repo, file_paths):
    """
    Analyze multiple files from a repo and return all findings.
    """
    all_findings = []
    for file_path in file_paths:
        try:
            file_content = repo.get_contents(file_path)
            code = file_content.decoded_content.decode('utf-8')
            findings = analyze_file(code, file_path)
            all_findings.extend(findings)
        except Exception as e:
            logger.error(f"Error analyzing file {file_path}: {e}")
            continue
    return all_findings

def comment_on_issue(repo, issue_number, comment_body):
    """
    Comment on a GitHub issue with the provided markdown body.
    """
    try:
        issue = repo.get_issue(int(issue_number))
        issue.create_comment(comment_body)
        return True
    except Exception as e:
        logger.error(f"Error posting comment: {e}")
        return False

def commit_file_change(repo, file_path, new_content, commit_message):
    """
    Commit code changes to a file in the repo.
    """
    try:
        file = repo.get_contents(file_path)
        repo.update_file(file_path, commit_message, new_content, file.sha)
        return True
    except Exception as e:
        logger.error(f"Error committing file change: {e}")
        return False
