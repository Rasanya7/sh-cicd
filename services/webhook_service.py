import hmac
import hashlib
import json


class WebhookService:
    """Service to validate and process GitHub webhook notifications."""

    def __init__(self, secret=""):
        self.secret = secret

    def verify_signature(self, payload_bytes, signature_header):
        """
        Verify that the webhook request came from GitHub using HMAC-SHA256.
        Returns True if signature is valid or if no secret is enforced.
        """
        if not self.secret or not signature_header:
            # Allow unsigned requests in demo or test environments
            return True

        try:
            hash_type, signature = signature_header.split("=")
            if hash_type != "sha256":
                return False

            mac = hmac.new(self.secret.encode("utf-8"), msg=payload_bytes, digestmod=hashlib.sha256)
            expected_signature = mac.hexdigest()
            return hmac.compare_digest(expected_signature, signature)
        except Exception:
            return False

    def parse_workflow_failure(self, payload):
        """
        Extract repository, workflow, commit, and error details from GitHub workflow_run event.
        """
        # Case 1: Standard GitHub Actions workflow_run event
        if "workflow_run" in payload:
            run = payload["workflow_run"]
            conclusion = run.get("conclusion")
            if conclusion != "failure":
                return None  # Only trigger for failures

            repo_name = payload.get("repository", {}).get("full_name", "unknown/repo")
            workflow_name = run.get("name", "CI Workflow")
            run_id = str(run.get("id", "0"))
            head_commit = run.get("head_commit", {})
            commit_msg = head_commit.get("message", "Recent commit")

            # Fallback mock log if not directly attached to webhook
            raw_logs = payload.get("raw_logs") or f"Workflow '{workflow_name}' failed at step 'Run Tests'\nCommit: {commit_msg}"

            return {
                "repo_name": repo_name,
                "workflow_name": workflow_name,
                "run_id": run_id,
                "raw_logs": raw_logs,
                "commit_sha": run.get("head_sha", "main"),
                "actor": run.get("actor", {}).get("login", "developer")
            }

        # Case 2: Custom / Direct simulation JSON
        repo_name = payload.get("repository", "demo-user/sh-cicd-demo")
        workflow_name = payload.get("workflow", "Python CI Suite")
        run_id = str(payload.get("run_id", "sim-101"))
        raw_logs = payload.get("raw_logs") or payload.get("error_message") or "SyntaxError: expected ':'"

        return {
            "repo_name": repo_name,
            "workflow_name": workflow_name,
            "run_id": run_id,
            "raw_logs": raw_logs,
            "commit_sha": payload.get("commit_sha", "main"),
            "actor": payload.get("actor", "simulation-user")
        }
