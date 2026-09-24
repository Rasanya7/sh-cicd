# Connecting Your GitHub Repository to Agentic Autofix Pipeline (SH-CICD)
### Complete Step-by-Step Guide for Automated Self-Healing CI/CD Pipelines

[![GitHub Actions](https://img.shields.io/badge/CI%2FCD-GitHub--Actions-black.svg?logo=githubactions)](https://github.com/features/actions)
[![Flask 3.0](https://img.shields.io/badge/Engine-Flask--3.0-green.svg)](https://flask.palletsprojects.com/)
[![Multi-Agent AI](https://img.shields.io/badge/AI-Multi--Agent%20Fleet-blueviolet.svg)](#architecture)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

This guide walks you through connecting **any GitHub repository** (public or private) to the **Agentic Autofix Pipeline (SH-CICD)**. Once connected, whenever a build or test fails in GitHub Actions, SH-CICD intercepts the failure, diagnoses root causes, generates surgical patches, executes pre-submission unit tests, audits security, and opens an **Auto-Fixed Pull Request** on your GitHub repository automatically.

---

## 1. System Architecture & Multi-Agent Flow

```mermaid
sequenceDiagram
    autonumber
    actor Dev as Developer
    participant GH as GitHub Actions (CI)
    participant Webhook as Webhook Receiver (/webhook/github)
    participant Dispatcher as 1. Dispatcher Agent
    participant Context as 2. Context Gatherer Agent
    participant Engineer as 3. Engineer Agent
    participant Reviewer as 4. Reviewer Agent
    participant Repo as GitHub Repository (REST API)

    Dev->>GH: git push (code with error)
    GH->>GH: Runs CI workflow (Tests Fail ❌)
    GH->>Webhook: Delivers HMAC-signed payload + failure logs
    Webhook->>Dispatcher: Forwards raw logs
    Dispatcher->>Dispatcher: Parses stack traces & classifies error
    Dispatcher->>Context: Sends failing file, line & category
    Context->>Repo: Fetches file AST, test files & recent commit diffs
    Context->>Engineer: Sends enriched codebase context bundle
    Engineer->>Engineer: Synthesizes surgical patch & runs sandbox unit tests
    Engineer->>Reviewer: Hands over verified patch & test results
    Reviewer->>Reviewer: Audits security (AST scan, blast radius, confidence >= 80%)
    Reviewer->>Repo: Creates branch sh-cicd/auto-fix-... & opens Pull Request 🚀
    Repo-->>Dev: Auto-Fixed PR ready for review & 1-click merge!
```

---

## 2. Prerequisites

Before connecting your repository, ensure you have:
- A **GitHub Account** and an existing repository (e.g. `your-username/your-python-repo`).
- **Python 3.10+** installed locally or on your server.
- **SH-CICD** running on port `5000` (`python app.py`).
- A tunneling tool like **ngrok** or **Cloudflare Tunnel** (if running SH-CICD locally) so GitHub can reach your webhook endpoint.

---

## 3. Step-by-Step Connection Process

### Step 1: Generate a GitHub Personal Access Token (PAT)

SH-CICD requires a GitHub token to fetch file contents, create feature branches, commit code repairs, and open Pull Requests.

1. Go to GitHub: **Settings** &rarr; **Developer Settings** &rarr; **Personal access tokens** &rarr; **Tokens (classic)** (or visit: [github.com/settings/tokens](https://github.com/settings/tokens)).
2. Click **Generate new token** &rarr; **Generate new token (classic)**.
3. Name your token: `SH-CICD-Agentic-Autofix`.
4. Select Expiration: **90 days** or **No expiration** (for continuous use).
5. Check the following scopes:
   - [x] **`repo`** (Full control of private repositories: `repo:status`, `repo_deployment`, `public_repo`, `repo:invite`)
   - [x] **`workflow`** (Update GitHub Action workflows)
   - [x] **`read:user`** & **`user:email`** (Read user profile data)
6. Click **Generate token** at the bottom.
7. **Copy and save your token** (e.g., `ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`). *You will not be able to see it again on GitHub.*

---

### Step 2: Configure SH-CICD Settings

You can configure SH-CICD either via the Web Dashboard or in the `.env` file:

#### Option A: Via Web UI (Recommended)
1. Open your browser and go to `http://localhost:5000/settings`.
2. Disable **Interactive Demo Mode** (toggle off to switch to **Live GitHub Mode**).
3. Fill in the integration fields:
   - **GitHub Personal Access Token (PAT):** Paste your token (`ghp_...`).
   - **Target Repository:** Enter your repo in format `owner/repo-name` (e.g., `octocat/my-python-app`).
   - **Webhook Secret:** Enter any secure random string (e.g., `my_agentic_autofix_secret_2026`).
   - **AI Provider:** Select `Google Gemini` (and provide `GEMINI_API_KEY`) or `OpenAI` (or choose `Offline Built-in Heuristic Engine` for zero-cost operation).
4. Click **Test Connection** to confirm authentication with GitHub.
5. Click **Save Settings**.

#### Option B: Via `.env` File
Edit your `.env` file in the project root:
```env
# Execution Mode
DEMO_MODE=false
AUTO_PR_ENABLED=true
MIN_CONFIDENCE_THRESHOLD=80.0

# GitHub Integration
GITHUB_TOKEN=ghp_yourActualGitHubPersonalAccessTokenHere
GITHUB_REPO=your-username/your-repo-name
WEBHOOK_SECRET=my_agentic_autofix_secret_2026

# AI Engine
AI_PROVIDER=gemini
GEMINI_API_KEY=AIzaSyYourGeminiApiKeyHere
AI_MODEL_NAME=gemini-1.5-flash
```

---

### Step 3: Expose Local Webhook Server to the Internet

Because SH-CICD runs on `http://127.0.0.1:5000`, GitHub's cloud servers need a publicly accessible HTTPS URL to deliver webhook notifications.

#### Using ngrok:
In a new terminal window, execute:
```bash
ngrok http 5000
```
ngrok will display an HTTPS forwarding address:
```
Forwarding: https://8f2a-103-21-125-9.ngrok-free.app -> http://localhost:5000
```
Your Webhook Endpoint URL is:
```
https://8f2a-103-21-125-9.ngrok-free.app/webhook/github
```

> [!TIP]
> Alternatively, you can use Cloudflare Tunnel (completely free without account limits):
> `cloudflared tunnel --url http://localhost:5000`

---

### Step 4: Configure GitHub Webhook in Your Target Repository

Now, connect your GitHub repository so it delivers workflow failure events to SH-CICD:

#### Method 1: 1-Click Setup via CLI Assistant
Run the interactive CLI helper in your terminal:
```bash
python connect_repo.py
```
This utility will automatically authenticate with your GitHub repository and register the webhook via GitHub REST API!

#### Method 2: Manual Webhook Setup on GitHub
1. Navigate to your target repository on GitHub: `https://github.com/<owner>/<repo>`.
2. Click **Settings** (top navigation tab) &rarr; **Webhooks** (left sidebar).
3. Click **Add webhook** (top right).
4. Enter the details:
   - **Payload URL:** `https://<your-ngrok-or-domain>.ngrok-free.app/webhook/github`
   - **Content type:** `application/json` *(Crucial: do NOT select application/x-www-form-urlencoded)*
   - **Secret:** Enter the exact `WEBHOOK_SECRET` configured in Step 2.
   - **SSL verification:** Enable SSL verification.
   - **Which events would you like to trigger this webhook?**
     - Select: **Let me select individual events.**
     - Check: [x] **Workflow runs**
     - Check: [x] **Check runs**
   - **Active:** Ensure the checkbox is checked.
5. Click **Add webhook**. GitHub will send a test ping with a green checkmark indicating success!

---

### Step 5: Add Self-Healing Workflow to Your Repository

In your target repository, create or update `.github/workflows/autofix.yml`:

```yaml
name: Python CI with Agentic Autofix

on:
  push:
    branches: [ "main", "master", "develop" ]
  pull_request:
    branches: [ "main", "master" ]

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout Code
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
          cache: 'pip'

      - name: Install Dependencies
        run: |
          python -m pip install --upgrade pip
          if [ -f requirements.txt ]; then pip install -r requirements.txt; fi

      - name: Run Test Suite
        id: run_tests
        run: |
          python -m unittest discover -s . -p "test_*.py"

      # Trigger SH-CICD Agentic Autofix if previous steps fail
      - name: Trigger Agentic Autofix on Failure
        if: failure()
        env:
          SH_CICD_WEBHOOK: ${{ secrets.SH_CICD_WEBHOOK_URL }}
        run: |
          echo "CI Failure detected! Notifying SH-CICD Multi-Agent Pipeline..."
          curl -X POST "$SH_CICD_WEBHOOK" \
            -H "Content-Type: application/json" \
            -d @- << 'EOF'
          {
            "repository": "${{ github.repository }}",
            "workflow": "${{ github.workflow }}",
            "run_id": "${{ github.run_id }}",
            "commit_sha": "${{ github.sha }}",
            "actor": "${{ github.actor }}",
            "raw_logs": "CI test execution failed in ${{ github.workflow }} (run #${{ github.run_id }})"
          }
          EOF
```

---

### Step 6: Configure Repository Secret on GitHub

1. In your target repository on GitHub:
   - Go to **Settings** &rarr; **Secrets and variables** &rarr; **Actions**.
2. Click **New repository secret**.
3. Set:
   - **Name:** `SH_CICD_WEBHOOK_URL`
   - **Secret:** `https://<your-ngrok-or-domain>.ngrok-free.app/webhook/github`
4. Click **Add secret**.

---

### Step 7: Live Verification Test (Watch Agentic Autofix in Action)

Now test the complete autonomous feedback loop:

1. In your connected repository, intentionally introduce an error (e.g. in `calculator.py`):
   ```python
   # Intentionally missing colon
   def add(a, b)
       return a + b
   ```
2. Commit and push:
   ```bash
   git add calculator.py
   git commit -m "test: simulate syntax failure"
   git push origin main
   ```
3. Watch GitHub Actions fail:
   - GitHub Actions runs the workflow and hits `SyntaxError: expected ':'`.
   - The `if: failure()` step triggers and sends the webhook payload to SH-CICD.
4. Watch the SH-CICD Command Center (`http://localhost:5000/dashboard`):
   - **Dispatcher Agent** activates: detects `SyntaxError` in `calculator.py` line 2.
   - **Context Gatherer Agent** activates: queries GitHub REST API for `calculator.py` and `test_calculator.py`.
   - **Engineer Agent** activates: fixes `def add(a, b):` and executes sandboxed unit tests (All Pass).
   - **Reviewer Agent** activates: scans for security risks, calculates confidence score (98.5%), and calls GitHub API.
5. Inspect GitHub:
   - Check your repository's Pull Requests tab (`https://github.com/<owner>/<repo>/pulls`).
   - A new Pull Request will be waiting:
     - Branch: `sh-cicd/auto-fix-XXXX`
     - Title: `[SH-CICD Auto-Fix] Resolve SyntaxError in calculator.py`
     - Description: Includes detailed diagnosis, agent breakdown, security verification, and test logs.
   - Click **Merge Pull Request** to deploy the fix!

---

## 4. Key Agent Roles & Guardrails

| Agent | Responsibility | Guardrail Enforced |
| :--- | :--- | :--- |
| **1. Dispatcher** | Log interception & error classification | Filters out non-code noise; limits error diagnosis payload to prevent prompt bloating. |
| **2. Context Gatherer** | GitHub REST API retrieval & AST bundle | Scope containment; fetches only the affected file, test fixtures, and recent commit diffs. |
| **3. Engineer** | Surgical code remediation & sandbox tests | Isolated execution (`tempfile`); strictly requires 100% unit test pass before submission. |
| **4. Reviewer** | Security audit & Pull Request dispatch | Scans for blacklisted calls (`os.system`, `subprocess`, `eval`, `rmtree`); requires $\ge 80\%$ confidence. |

---

## 5. Troubleshooting & FAQ

#### Q: The webhook delivers a 403 Invalid HMAC Signature error.
**Fix:** Verify that the `WEBHOOK_SECRET` in `.env` or `/settings` matches the secret configured in your GitHub Webhook. If left empty, HMAC verification is relaxed.

#### Q: GitHub Actions fails with `curl: (7) Failed to connect`.
**Fix:** Ensure your ngrok or Cloudflare tunnel is running and that the `SH_CICD_WEBHOOK_URL` secret points to the active forwarding URL.

#### Q: GitHub API returns 401 Unauthorized or 404 Not Found during PR creation.
**Fix:** Ensure your GitHub Personal Access Token has the `repo` scope enabled and that you have write/push access to the target repository.

#### Q: Can I run this in Docker or Deploy to Cloud?
**Fix:** Yes! You can deploy SH-CICD to Render, Railway, AWS EC2, or DigitalOcean:
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 5000
CMD ["python", "app.py"]
```
Once deployed, set the GitHub Webhook URL directly to `https://your-domain.com/webhook/github` without needing ngrok!
