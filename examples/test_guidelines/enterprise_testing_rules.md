# Enterprise Quality Engineering (QE) Testing Standards & Guidelines

## 1. Idempotency and State Isolation
- Every test function must be completely isolated and independently executable.
- Never rely on shared global state or ordering of test execution.
- Always utilize `pytest.fixture` with appropriate scopes (`function` by default) to set up fresh objects.
- Ensure all created mock records or files are properly torn down after execution.

## 2. Comprehensive Boundary and Edge Testing
- Validate edge values using `@pytest.mark.parametrize`:
  - Empty strings `""`, whitespace-only strings `"   "`, and null/None values.
  - Zero, negative numbers, extreme floats, and values exceeding maximum bounds.
  - Off-by-one boundary cases (e.g., minimum string lengths, expiration timestamps).
- Ensure explicit boundary assertions assert both return codes and side effects.

## 3. Explicit Exception Testing & Assertions
- Whenever the production code defines or raises custom exceptions (e.g. `UserNotFoundError`, `InsufficientFundsError`, `ValueError`), tests MUST assert that these exceptions are raised under failing conditions using `pytest.raises(ExceptionClass)`.
- Always verify the error message or error attributes to prevent silent false positives.

## 4. Strict Mocking and External I/O Decoupling
- Tests must never issue real HTTP requests, write to production databases, or mutate system environment variables.
- Use `unittest.mock.patch`, `monkeypatch`, or fixture stubs for any network or filesystem dependency.
- Always verify mock call arguments with `assert_called_once_with(...)`.

## 5. High Assertion Density and Semantic Quality
- Aim for an assertion density of at least 2.5 assertions per test function.
- Avoid vague tests that only execute code without verifying output dictionaries or object states.
- Follow the Arrange-Act-Assert (AAA) pattern with descriptive docstrings.
