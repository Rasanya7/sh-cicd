import os
import time
from dotenv import load_dotenv
from flask import Flask, render_template, request, jsonify, redirect, url_for

# Load environment variables
load_dotenv()

from database.database import init_db
from database.models import (
    get_failures,
    get_failure_by_id,
    get_agents,
    get_pull_requests,
    get_pull_request_by_id,
    get_agent_logs,
    get_settings,
    update_settings,
    get_stats
)
from services.orchestrator import MultiAgentOrchestrator
from services.webhook_service import WebhookService
from services.github_service import GitHubService

# Initialize Flask application
app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-sh-cicd-2026")

# Ensure database tables exist upon start
with app.app_context():
    init_db()


# =========================================================================
# WEB PAGES / TEMPLATE ROUTES
# =========================================================================

@app.route("/")
def index():
    """Project Landing Page with animated visual, features, and about."""
    return render_template("index.html")


@app.route("/dashboard")
def dashboard_view():
    """Main DevOps Command Center dashboard."""
    stats = get_stats()
    agents = get_agents()
    recent_failures = get_failures(limit=6)
    recent_prs = get_pull_requests(limit=6)
    return render_template(
        "dashboard.html",
        stats=stats,
        agents=agents,
        recent_failures=recent_failures,
        recent_prs=recent_prs
    )


@app.route("/failures")
def failures_view():
    """CI/CD Failures Audit table."""
    all_failures = get_failures(limit=100)
    return render_template("failures.html", failures=all_failures)


@app.route("/agents")
def agents_view():
    """Agent Fleet management and telemetry."""
    all_agents = get_agents()
    recent_logs = get_agent_logs(limit=25)
    return render_template("agents.html", agents=all_agents, logs=recent_logs)


@app.route("/analytics")
def analytics_view():
    """In-depth telemetry and Chart.js analytics."""
    stats = get_stats()
    return render_template("analytics.html", stats=stats)


@app.route("/pullrequests")
def pullrequests_view():
    """Auto-Fixed Pull Requests explorer."""
    prs = get_pull_requests(limit=100)
    return render_template("pullrequests.html", pull_requests=prs)


@app.route("/settings")
def settings_view():
    """System settings and credentials configuration."""
    current_settings = get_settings()
    return render_template("settings.html", settings=current_settings)


# =========================================================================
# REST API ENDPOINTS
# =========================================================================

@app.route("/api/failures", methods=["GET"])
def api_get_failures():
    """Fetch recent failures list."""
    failures = get_failures(limit=50)
    return jsonify({"failures": failures})


@app.route("/api/failures/<int:failure_id>", methods=["GET"])
def api_get_failure(failure_id):
    """Fetch details and logs for a single failure incident."""
    failure = get_failure_by_id(failure_id)
    if not failure:
        return jsonify({"error": "Failure not found"}), 404
    logs = get_agent_logs(failure_id=failure_id)
    return jsonify({"failure": failure, "logs": logs})


@app.route("/api/failures/<int:failure_id>/heal", methods=["POST"])
def api_retrigger_healing(failure_id):
    """Re-trigger the multi-agent healing sequence for an existing failure."""
    try:
        orchestrator = MultiAgentOrchestrator()
        result = orchestrator.run_healing_pipeline(failure_id=failure_id)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e), "success": False}), 500


@app.route("/api/agents", methods=["GET"])
def api_get_agents():
    """Fetch live statuses of all 4 AI agents."""
    agents = get_agents()
    return jsonify({"agents": agents})


@app.route("/api/analytics", methods=["GET"])
def api_get_analytics():
    """Fetch aggregated metrics for Chart.js dashboards."""
    stats = get_stats()
    agents = get_agents()
    stats["agents"] = agents
    return jsonify(stats)


@app.route("/api/pullrequests", methods=["GET"])
def api_get_pullrequests():
    """Fetch all generated pull requests."""
    prs = get_pull_requests(limit=50)
    return jsonify({"pull_requests": prs})


@app.route("/api/pullrequests/<int:pr_id>", methods=["GET"])
def api_get_pullrequest(pr_id):
    """Fetch single pull request details including patch diff."""
    pr = get_pull_request_by_id(pr_id)
    if not pr:
        return jsonify({"error": "Pull request not found"}), 404
    return jsonify({"pr": pr})


@app.route("/api/settings", methods=["POST"])
def api_update_settings():
    """Update system settings."""
    try:
        data = request.get_json() or {}
        update_settings(data)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


@app.route("/api/test-github", methods=["POST"])
def api_test_github():
    """Test GitHub PAT authentication."""
    data = request.get_json() or {}
    token = data.get("token", "")
    gh = GitHubService(token=token, demo_mode=False)
    is_auth = gh.is_authenticated()
    return jsonify({"authenticated": is_auth})


@app.route("/api/connect-repo/verify", methods=["POST"])
def api_connect_repo_verify():
    """Verify GitHub repository access and permissions using token."""
    data = request.get_json() or {}
    settings = get_settings()
    token = data.get("token") or settings.get("github_token", "")
    repo_name = data.get("repo_name") or settings.get("target_repo", "")
    demo_mode = data.get("demo_mode", False if token else True)

    gh = GitHubService(token=token, repo_name=repo_name, demo_mode=demo_mode)
    res = gh.verify_repository_access(repo_name)
    return jsonify(res)


@app.route("/api/connect-repo/setup-webhook", methods=["POST"])
def api_connect_repo_setup_webhook():
    """Automatically create webhook in target GitHub repository."""
    data = request.get_json() or {}
    settings = get_settings()
    token = data.get("token") or settings.get("github_token", "")
    repo_name = data.get("repo_name") or settings.get("target_repo", "")
    webhook_url = data.get("webhook_url", "")
    secret = data.get("webhook_secret") or settings.get("webhook_secret", "")

    if not webhook_url:
        return jsonify({"success": False, "error": "Webhook URL is required."}), 400

    gh = GitHubService(token=token, repo_name=repo_name, demo_mode=not bool(token))
    res = gh.create_repo_webhook(webhook_url=webhook_url, secret=secret)
    return jsonify(res)


@app.route("/api/connect-repo/workflow-yaml", methods=["GET"])
def api_connect_repo_workflow_yaml():
    """Return ready-to-use GitHub Actions workflow YAML for user repository."""
    webhook_url = request.args.get("webhook_url", "https://your-ngrok-or-domain.ngrok-free.app/webhook/github")
    workflow_yaml = f"""name: Python CI with Agentic Autofix

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
          echo "CI Failure detected! Dispatching to SH-CICD Agentic Autofix..."
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
    return jsonify({"yaml": workflow_yaml})


@app.route("/api/simulate-failure", methods=["POST"])
def api_simulate_failure():
    """
    Simulation endpoint to test end-to-end multi-agent healing:
    Dispatcher -> Context Gatherer -> Engineer -> Reviewer -> Auto-PR
    """
    data = request.get_json() or {}
    workflow_name = data.get("workflow_name", "Python CI Suite")
    error_type = data.get("error_type", "SyntaxError")
    raw_logs = data.get("raw_logs", "SyntaxError: expected ':'")
    repo_name = data.get("repo_name", "demo-user/sh-cicd-demo")

    failure_data = {
        "repo_name": repo_name,
        "workflow_name": workflow_name,
        "run_id": f"sim-{int(time.time())}",
        "error_type": error_type,
        "error_message": raw_logs.strip().splitlines()[-1] if raw_logs else "SyntaxError",
        "raw_logs": raw_logs
    }

    try:
        orchestrator = MultiAgentOrchestrator()
        result = orchestrator.run_healing_pipeline(failure_data=failure_data)
        return jsonify(result)
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# =========================================================================
# GITHUB ACTIONS WEBHOOK RECEIVER
# =========================================================================

@app.route("/webhook/github", methods=["POST"])
def github_webhook():
    """
    Webhook endpoint for GitHub Actions workflow_run events.
    Verifies HMAC SHA-256 signature and triggers the multi-agent pipeline upon failure.
    """
    settings = get_settings()
    secret = settings.get("webhook_secret", "")
    signature = request.headers.get("X-Hub-Signature-256")

    # Validate HMAC signature
    validator = WebhookService(secret=secret)
    if not validator.verify_signature(request.data, signature):
        return jsonify({"error": "Invalid HMAC signature"}), 403

    payload = request.get_json(silent=True) or {}
    event_type = request.headers.get("X-GitHub-Event", "workflow_run")

    failure_info = validator.parse_workflow_failure(payload)
    if not failure_info:
        return jsonify({"message": f"Event '{event_type}' ignored or was not a failure."}), 200

    try:
        orchestrator = MultiAgentOrchestrator()
        result = orchestrator.run_healing_pipeline(failure_data=failure_info)
        return jsonify({
            "message": "Multi-agent healing pipeline triggered successfully.",
            "result": result
        }), 200
    except Exception as e:
        return jsonify({"error": f"Failed to execute healing pipeline: {str(e)}"}), 500


# =========================================================================
# MAIN DRIVER
# =========================================================================

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print("\n" + "=" * 65)
    print(" 🚀 SH-CICD: Self-Healing CI/CD Multi-Agent AI System")
    print(f" 🌐 Access Dashboard at: http://127.0.0.1:{port}")
    print("=" * 65 + "\n")
    app.run(host="0.0.0.0", port=port, debug=True)
