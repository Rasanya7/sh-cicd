import os
import base64
import random
import requests


class GitHubService:
    """GitHub REST API Service with comprehensive Live and Demo Mode support."""

    def __init__(self, token=None, repo_name=None, demo_mode=True):
        self.token = token or os.environ.get("GITHUB_TOKEN", "")
        self.repo_name = repo_name or os.environ.get("GITHUB_REPO", "demo-user/sh-cicd-demo")
        self.demo_mode = demo_mode or (not bool(self.token))
        self.base_url = "https://api.github.com"
        self.headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "SH-CICD-Multi-Agent"
        }
        if self.token:
            self.headers["Authorization"] = f"token {self.token}"

    def is_authenticated(self):
        """Check if a valid GitHub API token is configured."""
        if self.demo_mode or not self.token:
            return False
        try:
            r = requests.get(f"{self.base_url}/user", headers=self.headers, timeout=5)
            return r.status_code == 200
        except Exception:
            return False

    def get_file_content(self, file_path, branch="main"):
        """Fetch the content of a file from GitHub or local demo repo in demo mode."""
        if self.demo_mode:
            # Look in demo_repo/ or project root
            base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
            local_paths = [
                os.path.join(base_dir, "demo_repo", file_path),
                os.path.join(base_dir, file_path),
                os.path.join(base_dir, "demo_repo", os.path.basename(file_path))
            ]
            for p in local_paths:
                if os.path.exists(p) and os.path.isfile(p):
                    with open(p, "r", encoding="utf-8") as f:
                        return f.read(), "mock-sha-12345"
            return "# Sample file content\ndef placeholder():\n    pass\n", "mock-sha-12345"

        url = f"{self.base_url}/repos/{self.repo_name}/contents/{file_path}?ref={branch}"
        try:
            res = requests.get(url, headers=self.headers, timeout=10)
            if res.status_code == 200:
                data = res.json()
                content = base64.b64decode(data["content"]).decode("utf-8")
                return content, data["sha"]
            return None, None
        except Exception as e:
            print(f"[GitHubService Error] Failed to read {file_path}: {e}")
            return None, None

    def get_recent_commits(self, limit=5):
        """Retrieve recent commit metadata."""
        if self.demo_mode:
            return [
                {"sha": "c1f7a9d", "message": "feat: add calculator arithmetic operations", "author": "DevOps Engineer"},
                {"sha": "a4b8e21", "message": "ci: update python CI workflow", "author": "CI Bot"},
                {"sha": "8d3e910", "message": "test: add calculator unit tests", "author": "QA Engineer"}
            ]

        url = f"{self.base_url}/repos/{self.repo_name}/commits?per_page={limit}"
        try:
            res = requests.get(url, headers=self.headers, timeout=10)
            if res.status_code == 200:
                commits = []
                for c in res.json():
                    commits.append({
                        "sha": c["sha"][:7],
                        "message": c["commit"]["message"],
                        "author": c["commit"]["author"]["name"]
                    })
                return commits
            return []
        except Exception as e:
            print(f"[GitHubService Error] Failed to fetch commits: {e}")
            return []

    def create_branch(self, base_branch="main", new_branch=None):
        """Create a new git branch for the auto-fix."""
        if not new_branch:
            new_branch = f"sh-cicd/auto-fix-{random.randint(1000, 9999)}"

        if self.demo_mode:
            return {
                "success": True,
                "branch": new_branch,
                "ref": f"refs/heads/{new_branch}",
                "mode": "demo"
            }

        try:
            # 1. Get base branch commit SHA
            ref_url = f"{self.base_url}/repos/{self.repo_name}/git/ref/heads/{base_branch}"
            res = requests.get(ref_url, headers=self.headers, timeout=10)
            if res.status_code != 200:
                return {"success": False, "error": f"Base branch '{base_branch}' not found."}
            base_sha = res.json()["object"]["sha"]

            # 2. Create new reference
            create_ref_url = f"{self.base_url}/repos/{self.repo_name}/git/refs"
            payload = {
                "ref": f"refs/heads/{new_branch}",
                "sha": base_sha
            }
            create_res = requests.post(create_ref_url, json=payload, headers=self.headers, timeout=10)
            if create_res.status_code in (200, 201):
                return {"success": True, "branch": new_branch, "ref": f"refs/heads/{new_branch}", "mode": "live"}
            return {"success": False, "error": create_res.json().get("message", "Failed to create branch")}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def commit_file_change(self, file_path, new_content, commit_message, branch, sha=None):
        """Commit modified file to the target branch."""
        if self.demo_mode:
            # In demo mode, apply locally if file exists in demo_repo
            base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
            local_target = os.path.join(base_dir, "demo_repo", os.path.basename(file_path))
            if os.path.exists(local_target):
                try:
                    with open(local_target, "w", encoding="utf-8") as f:
                        f.write(new_content)
                except Exception:
                    pass
            return {"success": True, "commit_sha": f"mock-{random.randint(100000, 999999)}", "mode": "demo"}

        try:
            # Get current SHA if not provided
            if not sha:
                _, sha = self.get_file_content(file_path, branch=branch)

            url = f"{self.base_url}/repos/{self.repo_name}/contents/{file_path}"
            encoded = base64.b64encode(new_content.encode("utf-8")).decode("utf-8")
            payload = {
                "message": commit_message,
                "content": encoded,
                "branch": branch
            }
            if sha:
                payload["sha"] = sha

            res = requests.put(url, json=payload, headers=self.headers, timeout=10)
            if res.status_code in (200, 201):
                return {"success": True, "commit_sha": res.json()["commit"]["sha"][:7], "mode": "live"}
            return {"success": False, "error": res.json().get("message", "Failed to commit change")}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def create_pull_request(self, title, body, head_branch, base_branch="main"):
        """Create a GitHub Pull Request for the healing branch."""
        if self.demo_mode:
            pr_num = random.randint(105, 999)
            return {
                "success": True,
                "pr_number": pr_num,
                "html_url": f"https://github.com/{self.repo_name}/pull/{pr_num}",
                "status": "OPEN",
                "mode": "demo"
            }

        url = f"{self.base_url}/repos/{self.repo_name}/pulls"
        payload = {
            "title": title,
            "body": body,
            "head": head_branch,
            "base": base_branch
        }
        try:
            res = requests.post(url, json=payload, headers=self.headers, timeout=10)
            if res.status_code in (200, 201):
                data = res.json()
                return {
                    "success": True,
                    "pr_number": data["number"],
                    "html_url": data["html_url"],
                    "status": "OPEN",
                    "mode": "live"
                }
            return {"success": False, "error": res.json().get("message", "Failed to create PR")}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def verify_repository_access(self, target_repo=None):
        """Verify repository existence and verify PAT push/pull permissions."""
        repo = target_repo or self.repo_name
        if self.demo_mode or not self.token:
            return {
                "valid": True,
                "mode": "demo",
                "repo": repo,
                "permissions": {"push": True, "pull": True, "admin": False},
                "default_branch": "main",
                "message": "Demo mode active (simulated GitHub connection)."
            }

        url = f"{self.base_url}/repos/{repo}"
        try:
            res = requests.get(url, headers=self.headers, timeout=10)
            if res.status_code == 200:
                data = res.json()
                permissions = data.get("permissions", {})
                can_push = permissions.get("push", False)
                return {
                    "valid": True,
                    "mode": "live",
                    "repo": repo,
                    "full_name": data.get("full_name"),
                    "default_branch": data.get("default_branch", "main"),
                    "permissions": permissions,
                    "can_push": can_push,
                    "private": data.get("private", False)
                }
            elif res.status_code == 404:
                return {"valid": False, "error": f"Repository '{repo}' not found or PAT lacks access."}
            elif res.status_code == 401:
                return {"valid": False, "error": "Invalid GitHub Personal Access Token (PAT)."}
            else:
                return {"valid": False, "error": res.json().get("message", f"HTTP {res.status_code}")}
        except Exception as e:
            return {"valid": False, "error": str(e)}

    def create_repo_webhook(self, webhook_url, secret=None):
        """Register a repository webhook for workflow_run and check_run events."""
        if self.demo_mode:
            return {
                "success": True,
                "mode": "demo",
                "webhook_id": 999999,
                "url": webhook_url,
                "events": ["workflow_run", "check_run"],
                "message": "Demo webhook simulated successfully."
            }

        url = f"{self.base_url}/repos/{self.repo_name}/hooks"
        payload = {
            "name": "web",
            "active": True,
            "events": ["workflow_run", "check_run"],
            "config": {
                "url": webhook_url,
                "content_type": "json",
                "secret": secret or "",
                "insecure_ssl": "0"
            }
        }
        try:
            res = requests.post(url, json=payload, headers=self.headers, timeout=10)
            if res.status_code in (200, 201):
                data = res.json()
                return {
                    "success": True,
                    "mode": "live",
                    "webhook_id": data.get("id"),
                    "url": webhook_url,
                    "events": data.get("events", [])
                }
            return {
                "success": False,
                "error": res.json().get("message", "Failed to create webhook.")
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_workflow_run_logs(self, run_id):
        """Retrieve failure logs from GitHub Actions jobs for a specific workflow run."""
        if self.demo_mode or not self.token:
            return None

        url = f"{self.base_url}/repos/{self.repo_name}/actions/runs/{run_id}/jobs"
        try:
            res = requests.get(url, headers=self.headers, timeout=10)
            if res.status_code != 200:
                return None
            jobs = res.json().get("jobs", [])
            for job in jobs:
                if job.get("conclusion") == "failure":
                    job_id = job.get("id")
                    logs_url = f"{self.base_url}/repos/{self.repo_name}/actions/jobs/{job_id}/logs"
                    log_res = requests.get(logs_url, headers=self.headers, timeout=15)
                    if log_res.status_code == 200:
                        return log_res.text
            return None
        except Exception as e:
            print(f"[GitHubService Error] Could not fetch workflow run logs: {e}")
            return None

