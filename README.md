# DevAgent Swarm 🚀🤖

**AI-Powered Code Review & Auto-Fix for GitHub Repositories**

---

## Overview

DevAgent Swarm is an intelligent agent platform that automatically reviews your code for security, quality, and testing issues—then suggests and applies fixes with a single click. Seamlessly integrated with GitHub, it empowers developers to ship safer, cleaner code faster.

---

## Features

- **🔒 Security & Quality Analysis:** Instantly scan your repo for vulnerabilities, code smells, and best practice violations.
- **🛠️ Auto-Fix & Commit:** Review AI-generated code fixes and commit them directly to your GitHub repo.
- **📊 Interactive Dashboard:** Visualize findings, filter by severity, and track your code health.
- **💬 Issue Commenting:** Automatically post findings and fixes to GitHub issues for team collaboration.
- **📥 Report Export:** Download detailed markdown reports for compliance or sharing.
- **⚡ Multi-file & Multi-repo Support:** Analyze and fix multiple files or repositories at once.
- **🔑 Secure Authentication:** All credentials handled securely—no hardcoding.

---

## How It Works

1. **Connect your GitHub account** using a personal access token.
2. **Select a repository and files** to analyze.
3. **Run the AI agent** to detect issues and get actionable recommendations.
4. **Review and apply fixes** with one click, then commit changes to GitHub.
5. **Comment on issues** and download reports for documentation.

---

## Built With

- **Python**
- **Streamlit** (frontend dashboard)
- **Amazon Bedrock** (LLM-powered analysis)
- **GitHub API** (repo access, issue commenting, auto-commit)
- **PostgreSQL** (optional, for storing results)
- **PyGithub, dotenv, pandas, matplotlib**

---

## Getting Started

1. Clone this repo:
    ```bash
    git clone https://github.com/<your-username>/<your-repo>.git
    cd <your-repo>
    ```
2. Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```
3. Add your `.env` file with your GitHub token and other secrets (never commit this file!).
4. Run the dashboard:
    ```bash
    streamlit run frontend/full_dashboard.py
    ```

---


---

## Why DevAgent Swarm?

- **Save time:** Automate tedious code reviews and remediation.
- **Ship safer code:** Catch vulnerabilities before they reach production.
- **Collaborate easily:** Share findings and fixes with your team.
- **Modern workflow:** All-in-one dashboard, no manual setup.

---

## License

MIT

---

## Contributing

We welcome contributions! Please open issues or submit PRs for improvements.

---

## Contact

Questions or feedback? [Open an issue](https://github.com/<your-username>/<your-repo>/issues) or email us at <your-
