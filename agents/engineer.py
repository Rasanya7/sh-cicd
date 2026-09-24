import time
from database.models import update_agent_status, create_agent_log


class EngineerAgent:
    """
    AGENT 3: ENGINEER AGENT
    - Ingests failure diagnosis and codebase context
    - Identifies root cause
    - Generates a minimal surgical code fix
    - Creates a unified git diff
    - Sandboxes the fix and runs unit tests via TestService
    - Packages proposed fix and test validation results for Reviewer Agent
    """

    def __init__(self, ai_service, test_service):
        self.name = "Engineer"
        self.ai_service = ai_service
        self.test_service = test_service

    def process(self, failure_id, context_bundle):
        """
        Synthesize solution, create patch, and validate with tests.
        Returns remediation package.
        """
        start_time = time.time()
        diagnosis = context_bundle["diagnosis"]
        source_code = context_bundle["source_code"]
        failing_file = context_bundle["failing_file"]

        update_agent_status(
            self.name,
            status="ACTIVE",
            current_task=f"Generating self-healing patch for {failing_file} (failure #{failure_id})"
        )

        # 1. Generate code fix using AI Service
        fix_result = self.ai_service.generate_code_fix(
            error_info=diagnosis,
            file_content=source_code,
            repo_context=context_bundle.get("test_code")
        )

        fixed_content = fix_result["fixed_content"]
        diff = fix_result["diff"]
        explanation = fix_result["explanation"]

        # 2. Run automated validation tests against patched code
        update_agent_status(
            self.name,
            status="BUSY",
            current_task=f"Executing sandboxed pre-submission tests for {failing_file}..."
        )

        test_outcome = self.test_service.run_tests_with_patch(
            patched_code=fixed_content,
            target_filename=failing_file,
            test_filename=context_bundle.get("test_filename", "test_calculator.py")
        )

        latency_ms = (time.time() - start_time) * 1000

        test_status_str = "PASSED" if test_outcome["passed"] else "FAILED"
        summary = (
            f"Generated patch for {failing_file}: '{explanation}'. "
            f"Pre-submission testing: {test_status_str}."
        )
        create_agent_log(failure_id, self.name, "Patch Synthesis & Test Validation", summary)

        update_agent_status(
            self.name,
            status="IDLE",
            current_task="Ready to construct next code fix",
            increment_completed=True,
            is_success=test_outcome["passed"],
            latency_ms=latency_ms
        )

        return {
            "failure_id": failure_id,
            "failing_file": failing_file,
            "original_code": source_code,
            "fixed_code": fixed_content,
            "diff": diff,
            "explanation": explanation,
            "test_outcome": test_outcome,
            "file_sha": context_bundle.get("file_sha")
        }
