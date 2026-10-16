"""Isolated test execution sandbox using subprocess and pytest."""

import os
import sys
import tempfile
import time
import subprocess
import re
from pathlib import Path
from typing import Optional, List
from qualiagent.core.state import ExecutionResult, FailedTestDetail
from qualiagent.config import settings


class TestSandbox:
    """Safely executes generated pytest code in an isolated subprocess."""

    # Prevent pytest from attempting to collect TestSandbox as a test class
    __test__ = False

    def __init__(self, timeout_seconds: Optional[int] = None):
        self.timeout = timeout_seconds or settings.sandbox_timeout_seconds

    def execute_tests(
        self,
        source_code: str,
        test_code: str,
        module_name: str = "target_module",
    ) -> ExecutionResult:
        """Executes test_code against source_code in an isolated environment."""
        start_time = time.time()

        # Create temporary directory for isolated execution
        with tempfile.TemporaryDirectory(prefix="qualiagent_sandbox_") as tmpdir:
            tmppath = Path(tmpdir)

            # Ensure valid module name
            clean_module_name = re.sub(r"[^a-zA-Z0-9_]", "_", module_name)
            if not clean_module_name or clean_module_name[0].isdigit():
                clean_module_name = f"mod_{clean_module_name}"

            source_file = tmppath / f"{clean_module_name}.py"
            test_file = tmppath / f"test_{clean_module_name}.py"

            # Replace any generic import references to the module name if needed
            adjusted_test_code = test_code
            if f"import {clean_module_name}" not in adjusted_test_code and f"from {clean_module_name}" not in adjusted_test_code:
                # If the test imports something else or relative, ensure clean_module_name is imported
                pass

            source_file.write_text(source_code, encoding="utf-8")
            test_file.write_text(adjusted_test_code, encoding="utf-8")

            # Environment with PYTHONPATH set to the sandbox tmpdir
            env = os.environ.copy()
            env["PYTHONPATH"] = f"{tmpdir}{os.pathsep}{env.get('PYTHONPATH', '')}"

            # Run pytest via current python interpreter
            cmd = [
                sys.executable,
                "-m",
                "pytest",
                str(test_file),
                "-v",
                "--tb=short",
                "-o",
                "python_files=test_*.py",
            ]

            try:
                proc = subprocess.run(
                    cmd,
                    cwd=tmpdir,
                    env=env,
                    capture_output=True,
                    text=True,
                    timeout=self.timeout,
                )
                duration = time.time() - start_time
                stdout = proc.stdout
                stderr = proc.stderr
                combined_output = f"{stdout}\n{stderr}".strip()

                return self._parse_pytest_output(
                    exit_code=proc.returncode,
                    output=combined_output,
                    duration=duration,
                )

            except subprocess.TimeoutExpired:
                duration = time.time() - start_time
                return ExecutionResult(
                    success=False,
                    total_tests=0,
                    passed=0,
                    failed=0,
                    errors=1,
                    output="Test execution timed out after {self.timeout}s.",
                    error_message=f"Timeout expired ({self.timeout}s)",
                    duration_seconds=duration,
                    failed_tests=[
                        FailedTestDetail(
                            test_name="TimeoutError",
                            error_type="TimeoutExpired",
                            stack_trace=f"Execution exceeded timeout limit of {self.timeout} seconds.",
                        )
                    ],
                )
            except Exception as e:
                duration = time.time() - start_time
                return ExecutionResult(
                    success=False,
                    total_tests=0,
                    passed=0,
                    failed=0,
                    errors=1,
                    output=str(e),
                    error_message=str(e),
                    duration_seconds=duration,
                    failed_tests=[
                        FailedTestDetail(
                            test_name="ExecutionException",
                            error_type=type(e).__name__,
                            stack_trace=str(e),
                        )
                    ],
                )

    def _parse_pytest_output(
        self, exit_code: int, output: str, duration: float
    ) -> ExecutionResult:
        """Parses pytest terminal output into structured ExecutionResult."""
        passed = 0
        failed = 0
        errors = 0
        skipped = 0

        # Match summary line: e.g. "== 4 passed, 1 failed in 0.12s =="
        passed_match = re.search(r"(\d+)\s+passed", output)
        if passed_match:
            passed = int(passed_match.group(1))

        failed_match = re.search(r"(\d+)\s+failed", output)
        if failed_match:
            failed = int(failed_match.group(1))

        errors_match = re.search(r"(\d+)\s+error(?:s)?", output)
        if errors_match:
            errors = int(errors_match.group(1))

        skipped_match = re.search(r"(\d+)\s+skipped", output)
        if skipped_match:
            skipped = int(skipped_match.group(1))

        total_tests = passed + failed + errors

        # Extract failed test details
        failed_tests: List[FailedTestDetail] = []

        # 1. First parse FAILURES blocks
        if "FAILURES" in output or "ERRORS" in output:
            failure_sections = re.split(r"_{3,}\s+([^\n]+?)\s+_{3,}", output)
            if len(failure_sections) > 1:
                # Every odd index is test name, even index is stack trace
                for i in range(1, len(failure_sections), 2):
                    t_name = failure_sections[i].strip()
                    s_trace = failure_sections[i + 1] if i + 1 < len(failure_sections) else ""

                    # Identify error type from traceback
                    err_match = re.search(r"\n([A-Za-z0-9_]+Error|[A-Za-z0-9_]+Exception):", s_trace)
                    if err_match:
                        err_type = err_match.group(1)
                    elif "assert " in s_trace or "E   assert" in s_trace:
                        err_type = "AssertionError"
                    else:
                        err_type = "TestFailure"

                    failed_tests.append(
                        FailedTestDetail(
                            test_name=t_name,
                            error_type=err_type,
                            stack_trace=s_trace.strip()[:1000],  # truncated for brevity
                        )
                    )

        # 2. Fallback to short summary info if failures block was missing or empty
        if not failed_tests and (failed > 0 or errors > 0):
            summary_matches = re.finditer(r"FAILED\s+(?:.*?)::([a-zA-Z0-9_]+)\s*(?:-\s*(.*))?", output)
            for sm in summary_matches:
                t_name = sm.group(1)
                reason = sm.group(2) or "Test assertion failed"
                err_type = "AssertionError" if "assert" in reason else "TestFailure"
                failed_tests.append(
                    FailedTestDetail(
                        test_name=t_name,
                        error_type=err_type,
                        stack_trace=reason[:1000],
                    )
                )

        # Success is strictly exit_code == 0 and at least 1 test passed
        is_success = (exit_code == 0) and (passed > 0) and (failed == 0) and (errors == 0)

        # Fallback if pytest collected 0 tests but succeeded
        if total_tests == 0 and exit_code == 0:
            is_success = False

        return ExecutionResult(
            success=is_success,
            total_tests=total_tests,
            passed=passed,
            failed=failed,
            errors=errors,
            skipped=skipped,
            output=output,
            error_message=None if is_success else f"Tests failed: {failed} failed, {errors} errors",
            duration_seconds=round(duration, 3),
            failed_tests=failed_tests,
        )
