"""Machine-readable engineering lessons distilled from verified Advait failures.

These are guardrails for future agents and reviewers, not proof that all legacy
components have already been migrated.
"""
ENGINEERING_LESSONS = (
    {
        "id": "FOUNDATION-001",
        "title": "SQLite transaction context is not connection lifecycle management",
        "trigger": "ResourceWarning and open SQLite handles in legacy TaskQueue/provider ledger",
        "root_cause": "sqlite3.Connection context manager commits or rolls back but does not close the connection",
        "mandatory_rule": "New SQLite code must use core.managed_sqlite_v1.managed_connection",
        "verification": "Test connection closure on success and exception; test nested parent path creation",
        "status": "ENFORCED_FOR_V2_COMPONENTS_ONLY",
    },
    {
        "id": "FOUNDATION-002",
        "title": "Create runtime paths before opening persistent resources",
        "trigger": "AI Developer workflow failed with sqlite3.OperationalError unable to open database file",
        "root_cause": "The runner temporary directory was not created before SQLite initialized its database",
        "mandatory_rule": "Create and validate parent directories before opening file-backed databases or writing reports",
        "verification": "Integration test uses a previously nonexistent nested directory",
        "status": "FIXED_IN_AI_DEVELOPER_CLI_AND_ENFORCED_BY_SHARED_SQLITE_HELPER",
    },
    {
        "id": "FOUNDATION-003",
        "title": "Unit tests do not replace workflow-environment integration tests",
        "trigger": "98 tests and compile checks passed but live GitHub Actions execution failed",
        "root_cause": "Tests did not exercise the actual runner temporary-path initialization path",
        "mandatory_rule": "Every workflow path must have a local integration test for arguments, directories, artifacts and failure behavior",
        "verification": "Run CLI against temporary paths without provider/network access, then perform a manual live provider smoke test",
        "status": "PARTIALLY_ENFORCED",
    },
    {
        "id": "FOUNDATION-004",
        "title": "A green CI run proves only the checks that were executed",
        "trigger": "Static and mocked tests were mistaken for proof of live provider operation",
        "root_cause": "Verification scope was not clearly separated from external integration proof",
        "mandatory_rule": "Report unit, integration, live-provider and production evidence as separate statuses",
        "verification": "Every report states exact test scope and unverified dependencies",
        "status": "ENFORCED_IN_DOCUMENTATION_AND_REPORT_SCHEMA",
    },
    {
        "id": "FOUNDATION-005",
        "title": "Never allow an AI finding to become an automatic patch",
        "trigger": "Planned transition from AI Developer to self-healing",
        "root_cause": "Model output can be incorrect or manipulated by source text",
        "mandatory_rule": "Require exact evidence, independent reproduction, isolated patch, tests, review and owner approval",
        "verification": "Reject unsupported findings and block writes in read-only audit mode",
        "status": "ENFORCED_IN_AI_DEVELOPER_V1",
    },
    {
        "id": "FOUNDATION-006",
        "title": "Test database rollback with transactional operations",
        "trigger": "Initial rollback test assumed CREATE TABLE would be rolled back",
        "root_cause": "SQLite transaction behavior for DDL differs from ordinary DML under Python sqlite3 transaction control",
        "mandatory_rule": "Use INSERT/UPDATE/DELETE assertions to test rollback; test schema setup separately",
        "verification": "Raise after a DML write and verify the row is absent after reopening the database",
        "status": "ENFORCED_IN_FOUNDATION_TESTS",
    },
)


def lessons_for_agent():
    """Return a JSON-serializable copy suitable for an agent system prompt."""
    return [dict(item) for item in ENGINEERING_LESSONS]
