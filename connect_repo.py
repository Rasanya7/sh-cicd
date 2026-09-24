"""
SH-CICD: Agentic Autofix Pipeline in GitHub
connect_repo.py - Interactive CLI Helper to Connect GitHub Repositories
"""

import os
import sys
import json
import argparse
import requests
from dotenv import load_dotenv

# Load existing environment variables
load_dotenv()

from database.database import init_db
from database.models import get_settings, update_settings
from services.github_service import GitHubService


def print_banner():
    print("\n" + "=" * 70)
    print(" 🤖 Agentic Autofix Pipeline in GitHub (SH-CICD)")
    print(" 🔗 Interactive Repository Connection & Setup Assistant")
    print("=" * 70 + "\n")


def prompt_or_default(prompt_text, default_val=""):
    if default_val:
        res = input(f"{prompt_text} [{default_val}]: ").strip()
        return res if res else default_val
    return input(f"{prompt_text}: ").strip()


def run_connect_wizard():
    print_banner()
    init_db()
    current_settings = get_settings()

    print("Step 1: GitHub Authentication & Target Repository")
    print("-" * 50)
    
    saved_token = current_settings.get("github_token", "")
    token = prompt_or_default("Enter your GitHub Personal Access Token (PAT)", saved_token)

    saved_repo = current_settings.get("target_repo", "your-username/your-repo")
    target_repo = prompt_or_default("Enter target GitHub repository (owner/repo)", saved_repo)

    webhook_secret = prompt_or_default("Enter Webhook Secret (HMAC key)", current_settings.get("webhook_secret", "sh_cicd_secret_2026"))

    print("\n[+] Validating token and repository access with GitHub REST API...")
    gh = GitHubService(token=token, repo_name=target_repo, demo_mode=False)

    if not gh.is_authenticated():
        print("❌ [ERROR] Could not authenticate with GitHub using this token.")
        print("   Please check token expiration and ensure scopes 'repo' and 'workflow' are enabled.")
        sys.exit(1)

    print("✅ [SUCCESS] GitHub PAT is valid and authenticated!")

    repo_info = gh.verify_repository_access(target_repo)
    if not repo_info.get("valid"):
        print(f"❌ [ERROR] Could not access repository '{target_repo}': {repo_info.get('error')}")
        sys.exit(1)

    print(f"✅ [SUCCESS] Repository verified: {repo_info.get('full_name')} (Default branch: {repo_info.get('default_branch')})")
    permissions = repo_info.get("permissions", {})
    if permissions.get("push"):
        print("✅ [SUCCESS] PAT has write/push permissions to open Auto-Fixed PRs!")
    else:
        print("⚠️ [WARNING] PAT has read-only access. Auto-Fixed PR creation requires write/push permissions.")

    # Save to database and .env
    update_settings({
        "github_token": token,
        "target_repo": target_repo,
        "webhook_secret": webhook_secret,
        "demo_mode": 0
    })
    print("\n💾 Settings saved to SH-CICD local database and configuration!")

    print("\nStep 2: Expose SH-CICD Webhook Endpoint")
    print("-" * 50)
    print("GitHub Actions needs to deliver webhooks to your SH-CICD server.")
    print("If running locally, start an ngrok or Cloudflare tunnel:")
    print("   Run in a separate terminal: ngrok http 5000")
    print("   Or: cloudflared tunnel --url http://localhost:5000")
    print("")

    default_url = "https://your-tunnel.ngrok-free.app/webhook/github"
    webhook_url = prompt_or_default("Enter your public Webhook URL", default_url)

    if "ngrok" in webhook_url or "http" in webhook_url:
        if not webhook_url.endswith("/webhook/github"):
            webhook_url = webhook_url.rstrip("/") + "/webhook/github"
        print(f"Webhook URL set to: {webhook_url}")

        auto_reg = input("\nWould you like to automatically register this webhook in your GitHub repo? (y/n) [y]: ").strip().lower()
        if auto_reg != "n":
            print(f"Registering webhook on https://github.com/{target_repo}...")
            reg_res = gh.create_repo_webhook(webhook_url=webhook_url, secret=webhook_secret)
            if reg_res.get("success"):
                print(f"✅ [SUCCESS] Webhook created on GitHub! (Webhook ID: {reg_res.get('webhook_id')})")
            else:
                print(f"⚠️ [NOTICE] Automatic registration result: {reg_res.get('error')}")
                print("   You can still configure it manually in GitHub -> Settings -> Webhooks.")

    print("\nStep 3: GitHub Actions Workflow Configuration")
    print("-" * 50)
    print("Add the following workflow file to your repository at:")
    print(f"   {target_repo}: .github/workflows/autofix.yml\n")

    workflow_content = f"""name: Python CI with Agentic Autofix

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

      - name: Trigger Agentic Autofix on Failure
        if: failure()
        env:
          SH_CICD_WEBHOOK: ${{{{ secrets.SH_CICD_WEBHOOK_URL }}}}
        run: |
          echo "CI Failure detected! Notifying SH-CICD Agentic Autofix..."
          curl -X POST "${{SH_CICD_WEBHOOK:-{webhook_url}}}" \\
            -H "Content-Type: application/json" \\
            -d @- << 'EOF'
          {{
            "repository": "${{{{ github.repository }}}}",
            "workflow": "${{{{ github.workflow }}}}",
            "run_id": "${{{{ github.run_id }}}}",
            "commit_sha": "${{{{ github.sha }}}}",
            "actor": "${{{{ github.actor }}}}",
            "raw_logs": "CI test failure in ${{{{ github.workflow }}}} (run #${{{{ github.run_id }}}})"
          }}
          EOF
"""
    print(workflow_content)

    save_local = input("Would you like to save this sample workflow to .github/workflows/autofix.yml locally? (y/n) [n]: ").strip().lower()
    if save_local == "y":
        wf_dir = os.path.join(os.path.dirname(__file__), ".github", "workflows")
        os.makedirs(wf_dir, exist_ok=True)
        wf_path = os.path.join(wf_dir, "autofix.yml")
        with open(wf_path, "w", encoding="utf-8") as f:
            f.write(workflow_content)
        print(f"✅ Saved workflow file to: {wf_path}")

    print("\nStep 4: Configure GitHub Repository Secret")
    print("-" * 50)
    print(f"In your repository (https://github.com/{target_repo}/settings/secrets/actions):")
    print(f"1. Click 'New repository secret'")
    print(f"2. Name: SH_CICD_WEBHOOK_URL")
    print(f"3. Value: {webhook_url}")
    print(f"4. Click 'Add secret'")

    print("\n" + "=" * 70)
    print(" 🎉 Connection Setup Complete!")
    print(f" Your repository '{target_repo}' is now ready for Agentic Autofixing!")
    print(" Whenever a build or test fails in GitHub Actions, SH-CICD will:")
    print(" 1. Diagnose error logs (Dispatcher)")
    print(" 2. Fetch repo files & test suites (Context Gatherer)")
    print(" 3. Synthesize minimal code fixes & run sandbox tests (Engineer)")
    print(" 4. Audit security & open an Auto-Fixed Pull Request on GitHub (Reviewer)")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    run_connect_wizard()
