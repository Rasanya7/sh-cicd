import time
from database.models import (
    create_failure,
    get_failure_by_id,
    update_failure_status,
    get_settings
)
from services.ai_service import AIService
from services.github_service import GitHubService
from services.test_service import TestService
from agents.dispatcher import DispatcherAgent
from agents.context_gatherer import ContextGathererAgent
from agents.engineer import EngineerAgent
from agents.reviewer import ReviewerAgent


class MultiAgentOrchestrator:
    """
    Coordinates the execution of all 4 AI agents in a continuous self-healing cycle:
    Dispatcher -> Context Gatherer -> Engineer -> Reviewer
    """

    def __init__(self):
        settings = get_settings()
        self.ai_service = AIService(
            provider=settings.get("ai_provider", "demo"),
            api_key=settings.get("ai_api_key", ""),
            model_name=settings.get("ai_model_name", "gemini-1.5-flash")
        )
        self.github_service = GitHubService(
            token=settings.get("github_token", ""),
            repo_name=settings.get("target_repo", "demo-user/sh-cicd-demo"),
            demo_mode=bool(settings.get("demo_mode", 1))
        )
        self.test_service = TestService()

        # Instantiate 4 specialized agents
        self.dispatcher = DispatcherAgent(self.ai_service)
        self.context_gatherer = ContextGathererAgent(self.github_service)
        self.engineer = EngineerAgent(self.ai_service, self.test_service)
        self.reviewer = ReviewerAgent(self.ai_service, self.github_service)

    def run_healing_pipeline(self, failure_id=None, failure_data=None):
        """
        Execute the full 4-agent healing pipeline end-to-end.
        """
        settings = get_settings()
        min_conf = float(settings.get("min_confidence_threshold", 80.0))

        # 1. Ensure failure record in DB
        if failure_id is None:
            raw_logs = failure_data.get("raw_logs", "")
            error_type = failure_data.get("error_type", "UnknownError")
            error_msg = failure_data.get("error_message", raw_logs[:120])
            repo_name = failure_data.get("repo_name", self.github_service.repo_name)
            workflow_name = failure_data.get("workflow_name", "Python CI Suite")
            run_id = failure_data.get("run_id", f"run-{int(time.time())}")

            failure_id = create_failure(
                repo_name=repo_name,
                workflow_name=workflow_name,
                run_id=run_id,
                error_type=error_type,
                error_message=error_msg,
                raw_logs=raw_logs,
                status="IN_PROGRESS"
            )
            failure_info = failure_data
        else:
            db_fail = get_failure_by_id(failure_id)
            if not db_fail:
                raise ValueError(f"Failure #{failure_id} not found.")
            update_failure_status(failure_id, "IN_PROGRESS")
            failure_info = {
                "repo_name": db_fail["repo_name"],
                "workflow_name": db_fail["workflow_name"],
                "run_id": db_fail["run_id"],
                "raw_logs": db_fail["raw_logs"],
                "error_type": db_fail["error_type"],
                "error_message": db_fail["error_message"]
            }

        steps_record = []

        # ==========================================
        # STEP 1: DISPATCHER AGENT
        # ==========================================
        diagnosis = self.dispatcher.process(failure_id, failure_info)
        steps_record.append({
            "agent": "Dispatcher",
            "status": "COMPLETED",
            "summary": f"Detected {diagnosis.get('error_type')} in {diagnosis.get('failing_file')} line {diagnosis.get('line_number')}.",
            "data": diagnosis
        })

        # Update failure error_type if diagnosed more accurately
        if diagnosis.get("error_type"):
            update_failure_status(failure_id, "IN_PROGRESS")

        # ==========================================
        # STEP 2: CONTEXT GATHERER AGENT
        # ==========================================
        context_bundle = self.context_gatherer.process(failure_id, diagnosis)
        steps_record.append({
            "agent": "Context Gatherer",
            "status": "COMPLETED",
            "summary": f"Loaded source for {context_bundle.get('failing_file')}, commit history, and test suite.",
            "data": {
                "failing_file": context_bundle.get("failing_file"),
                "lines_count": len(context_bundle.get("source_code", "").splitlines()),
                "test_suite": context_bundle.get("test_filename")
            }
        })

        # ==========================================
        # STEP 3: ENGINEER AGENT
        # ==========================================
        remediation = self.engineer.process(failure_id, context_bundle)
        steps_record.append({
            "agent": "Engineer",
            "status": "COMPLETED",
            "summary": f"Generated patch: '{remediation.get('explanation')}'. Pre-tests: {'PASSED' if remediation.get('test_outcome', {}).get('passed') else 'FAILED'}.",
            "data": {
                "diff": remediation.get("diff"),
                "test_outcome": remediation.get("test_outcome")
            }
        })

        # ==========================================
        # STEP 4: REVIEWER AGENT
        # ==========================================
        review_result = self.reviewer.process(failure_id, remediation, min_confidence=min_conf)
        steps_record.append({
            "agent": "Reviewer",
            "status": "COMPLETED" if review_result.get("approved") else "REJECTED",
            "summary": f"Verdict: {review_result.get('audit', {}).get('verdict')} with confidence {review_result.get('confidence', 0):.1f}%.",
            "data": review_result
        })

        return {
            "failure_id": failure_id,
            "success": review_result.get("approved", False),
            "verdict": review_result.get("audit", {}).get("verdict"),
            "confidence": review_result.get("confidence"),
            "pull_request": review_result.get("pull_request"),
            "steps": steps_record
        }
