import time
from database.models import update_agent_status, create_agent_log


class DispatcherAgent:
    """
    AGENT 1: DISPATCHER AGENT
    - Receives GitHub Actions CI/CD failure event & raw logs
    - Parses and analyzes error tracebacks
    - Classifies the failure category (Syntax, Dependency, Testing, Build, Runtime, Config)
    - Extracts failing file name, line numbers, and error summary
    - Packages a structured problem specification for Agent B (Context Gatherer)
    """

    def __init__(self, ai_service):
        self.name = "Dispatcher"
        self.ai_service = ai_service

    def process(self, failure_id, failure_info):
        """
        Execute Dispatcher diagnosis.
        Returns structured problem dictionary.
        """
        start_time = time.time()
        raw_logs = failure_info.get("raw_logs", "")

        # Set status to ACTIVE in database
        update_agent_status(
            self.name,
            status="ACTIVE",
            current_task=f"Analyzing CI/CD logs for failure #{failure_id} ({failure_info.get('workflow_name', 'CI')})"
        )

        # Diagnose using AI Service (LLM or Heuristic)
        diagnosis = self.ai_service.analyze_failure_log(raw_logs)

        # Add workflow and repo metadata
        diagnosis["repo_name"] = failure_info.get("repo_name", "demo-user/sh-cicd-demo")
        diagnosis["workflow_name"] = failure_info.get("workflow_name", "Python CI Suite")
        diagnosis["run_id"] = failure_info.get("run_id", "0")
        diagnosis["failure_id"] = failure_id

        latency_ms = (time.time() - start_time) * 1000

        # Log action to database
        summary = (
            f"Analyzed CI logs. Detected {diagnosis.get('error_type')} in "
            f"{diagnosis.get('failing_file') or 'unknown'} "
            f"(Line {diagnosis.get('line_number') or 'N/A'}). Category: {diagnosis.get('category')}."
        )
        create_agent_log(failure_id, self.name, "Log Analysis & Categorization", summary)

        # Reset agent status to IDLE and record completion
        update_agent_status(
            self.name,
            status="IDLE",
            current_task="Awaiting next CI/CD failure event",
            increment_completed=True,
            is_success=True,
            latency_ms=latency_ms
        )

        return diagnosis
