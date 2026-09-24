import os
import sys
import tempfile
import subprocess
import ast


class TestService:
    """Service to validate code patches via AST compilation and sandboxed test execution."""

    def __init__(self, demo_dir=None):
        self.demo_dir = demo_dir or os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "demo_repo")
        )

    def validate_syntax(self, code_str, filename="<string>"):
        """Check if Python code string compiles without syntax or indentation errors."""
        try:
            ast.parse(code_str, filename=filename)
            return {"valid": True, "error": None}
        except SyntaxError as se:
            return {
                "valid": False,
                "error": f"SyntaxError on line {se.lineno}: {se.msg}",
                "lineno": se.lineno
            }
        except Exception as e:
            return {"valid": False, "error": str(e)}

    def run_tests_with_patch(self, patched_code, target_filename="calculator.py", test_filename="test_calculator.py"):
        """
        Execute unit tests in a temporary isolated directory using the patched code file.
        Returns execution outcome and output.
        """
        # 1. Syntax check first
        syntax_check = self.validate_syntax(patched_code, filename=target_filename)
        if not syntax_check["valid"]:
            return {
                "passed": False,
                "tests_run": 0,
                "failures": 1,
                "errors": 1,
                "output": f"Pre-test Syntax Validation Failed: {syntax_check['error']}"
            }

        # 2. Setup temporary testing sandbox
        with tempfile.TemporaryDirectory() as tmpdir:
            temp_target_file = os.path.join(tmpdir, target_filename)
            temp_test_file = os.path.join(tmpdir, test_filename)

            # Write patched file
            with open(temp_target_file, "w", encoding="utf-8") as f:
                f.write(patched_code)

            # Copy or load test suite
            source_test_path = os.path.join(self.demo_dir, test_filename)
            if os.path.exists(source_test_path):
                with open(source_test_path, "r", encoding="utf-8") as f:
                    test_content = f.read()
                with open(temp_test_file, "w", encoding="utf-8") as f:
                    f.write(test_content)
            else:
                # Basic default test file
                with open(temp_test_file, "w", encoding="utf-8") as f:
                    f.write("""import unittest
from calculator import add
class BasicTest(unittest.TestCase):
    def test_add(self):
        self.assertEqual(add(1, 2), 3)
if __name__ == '__main__':
    unittest.main()
""")

            # Run tests via subprocess in isolated temp directory
            cmd = [sys.executable, "-m", "unittest", test_filename]
            try:
                result = subprocess.run(
                    cmd,
                    cwd=tmpdir,
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                output = (result.stdout + "\n" + result.stderr).strip()
                passed = (result.returncode == 0)

                return {
                    "passed": passed,
                    "returncode": result.returncode,
                    "output": output or ("Tests passed successfully." if passed else "Tests failed.")
                }
            except subprocess.TimeoutExpired:
                return {
                    "passed": False,
                    "returncode": -1,
                    "output": "Test execution timed out after 10 seconds."
                }
            except Exception as e:
                return {
                    "passed": False,
                    "returncode": -1,
                    "output": f"Sandbox error executing tests: {str(e)}"
                }
