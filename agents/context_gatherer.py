import time
import os
from database.models import update_agent_status, create_agent_log


class ContextGathererAgent:
    """
    AGENT 2: CONTEXT GATHERER AGENT
    - Connects to GitHub REST API / Repository Workspace
    - Fetches the source code of the failing file
    - Inspects project dependencies and configuration files
    - Retrieves recent git commit history to detect recent code changes
    - Locates associated unit test suites
    - Assembles comprehensive context for Agent C (Engineer Agent)
    """

    def __init__(self, github_service):
        self.name = "Context Gatherer"
        self.github_service = github_service

    def process(self, failure_id, diagnosis):
        """
        Gathers repository context based on the Dispatcher's diagnosis.
        Returns a context bundle dictionary.
        """
        start_time = time.time()
        failing_file = diagnosis.get("failing_file") or "calculator.py"

        update_agent_status(
            self.name,
            status="ACTIVE",
            current_task=f"Fetching codebase context and AST for {failing_file} (failure #{failure_id})"
        )

        # 1. Fetch file content from GitHub or demo_repo
        file_content, file_sha = self.github_service.get_file_content(failing_file)
        if not file_content:
            # Fallback to calculator.py
            file_content, file_sha = self.github_service.get_file_content("calculator.py")

        # 2. Fetch recent commits
        recent_commits = self.github_service.get_recent_commits(limit=3)

        # 3. Fetch test file context
        test_filename = f"test_{os.path.basename(failing_file)}"
        test_content, _ = self.github_service.get_file_content(test_filename)

        # 4. Fetch requirements/config
        reqs_content, _ = self.github_service.get_file_content("requirements.txt")

        context_bundle = {
            "failure_id": failure_id,
            "diagnosis": diagnosis,
            "failing_file": failing_file,
            "file_sha": file_sha,
            "source_code": file_content,
            "recent_commits": recent_commits,
            "test_filename": test_filename,
            "test_code": test_content,
            "dependencies": reqs_content
        }

        latency_ms = (time.time() - start_time) * 1000

        summary = (
            f"Retrieved {failing_file} ({len(file_content.splitlines()) if file_content else 0} lines). "
            f"Extracted {len(recent_commits)} recent commits and test suite '{test_filename}'."
        )
        create_agent_log(failure_id, self.name, "Repository Context Gathering", summary)

        update_agent_status(
            self.name,
            status="IDLE",
            current_task="Ready to inspect next repository failure",
            increment_completed=True,
            is_success=True,
            latency_ms=latency_ms
        )

        return context_bundle
