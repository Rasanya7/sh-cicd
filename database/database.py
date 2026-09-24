import sqlite3
import os
from datetime import datetime, timedelta

DB_FILE = os.path.join(os.path.dirname(__file__), "sh_cicd.db")


def get_db_connection():
    """Establish and return a SQLite connection with Row factory."""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """Initialize tables and seed initial records if empty."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # 1. Failures Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS failures (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        repo_name TEXT NOT NULL,
        workflow_name TEXT NOT NULL,
        run_id TEXT,
        error_type TEXT NOT NULL,
        error_message TEXT NOT NULL,
        raw_logs TEXT,
        status TEXT NOT NULL DEFAULT 'PENDING',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        resolved_at TIMESTAMP
    );
    """)

    # 2. Agents Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS agents (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        agent_name TEXT UNIQUE NOT NULL,
        status TEXT NOT NULL DEFAULT 'IDLE',
        current_task TEXT DEFAULT 'Waiting for workflow triggers...',
        completed_tasks INTEGER DEFAULT 0,
        successful_fixes INTEGER DEFAULT 0,
        failed_tasks INTEGER DEFAULT 0,
        avg_latency_ms REAL DEFAULT 420.0,
        last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # 3. Pull Requests Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS pull_requests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        failure_id INTEGER,
        pr_number INTEGER,
        repo_name TEXT NOT NULL,
        branch_name TEXT NOT NULL,
        fix_description TEXT NOT NULL,
        patch_diff TEXT,
        reviewer_status TEXT DEFAULT 'PENDING',
        reviewer_confidence REAL DEFAULT 0.0,
        test_status TEXT DEFAULT 'PENDING',
        status TEXT DEFAULT 'OPEN',
        html_url TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (failure_id) REFERENCES failures (id) ON DELETE SET NULL
    );
    """)

    # 4. Agent Logs Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS agent_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        failure_id INTEGER,
        agent_name TEXT NOT NULL,
        action TEXT NOT NULL,
        output_summary TEXT NOT NULL,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (failure_id) REFERENCES failures (id) ON DELETE CASCADE
    );
    """)

    # 5. Settings Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS settings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        github_token TEXT DEFAULT '',
        target_repo TEXT DEFAULT 'demo-user/sh-cicd-demo',
        webhook_secret TEXT DEFAULT 'demo_webhook_secret',
        ai_provider TEXT DEFAULT 'demo',
        ai_api_key TEXT DEFAULT '',
        ai_model_name TEXT DEFAULT 'gemini-1.5-flash',
        demo_mode BOOLEAN DEFAULT 1,
        auto_pr_enabled BOOLEAN DEFAULT 1,
        min_confidence_threshold REAL DEFAULT 80.0
    );
    """)

    conn.commit()
    seed_initial_data(cursor, conn)
    conn.close()


def seed_initial_data(cursor, conn):
    """Seed initial agent registry, default configuration, and demo baseline data."""
    # Seed Agents
    agents = [
        ("Dispatcher", "IDLE", "Awaiting GitHub Actions CI failure webhook", 14, 14, 0, 310.5),
        ("Context Gatherer", "IDLE", "Ready to fetch AST & repo file context", 14, 14, 0, 480.2),
        ("Engineer", "IDLE", "Ready to generate self-healing patches & run tests", 14, 13, 1, 950.0),
        ("Reviewer", "IDLE", "Standby for automated security and quality audit", 14, 13, 1, 520.4)
    ]

    for name, status, task, comp, succ, fail, lat in agents:
        cursor.execute("""
            INSERT OR IGNORE INTO agents (agent_name, status, current_task, completed_tasks, successful_fixes, failed_tasks, avg_latency_ms)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (name, status, task, comp, succ, fail, lat))

    # Seed Settings
    cursor.execute("SELECT COUNT(*) FROM settings")
    if cursor.fetchone()[0] == 0:
        cursor.execute("""
            INSERT INTO settings (github_token, target_repo, webhook_secret, ai_provider, ai_api_key, ai_model_name, demo_mode, auto_pr_enabled, min_confidence_threshold)
            VALUES ('', 'demo-user/sh-cicd-demo', 'demo_webhook_secret', 'demo', '', 'gemini-1.5-flash', 1, 1, 80.0)
        """)

    # Seed initial baseline failures and PRs if failures table is empty
    cursor.execute("SELECT COUNT(*) FROM failures")
    if cursor.fetchone()[0] == 0:
        now = datetime.now()
        seed_failures = [
            (
                "demo-user/sh-cicd-demo",
                "Python CI Suite",
                "run-882190",
                "SyntaxError",
                "SyntaxError: invalid syntax (calculator.py, line 4)",
                "File 'calculator.py', line 4\n    def add(a, b)\n                 ^\nSyntaxError: expected ':'",
                "RESOLVED",
                (now - timedelta(hours=5)).strftime("%Y-%m-%d %H:%M:%S"),
                (now - timedelta(hours=4, minutes=58)).strftime("%Y-%m-%d %H:%M:%S"),
            ),
            (
                "demo-user/sh-cicd-demo",
                "Backend Integration",
                "run-882155",
                "AssertionError",
                "AssertionError: assert divide(10, 2) == 4.0 != 5.0",
                "tests/test_calc.py:18: AssertionError: Expected 5.0 but got 4.0\nFAILED tests/test_calc.py::test_divide",
                "RESOLVED",
                (now - timedelta(hours=22)).strftime("%Y-%m-%d %H:%M:%S"),
                (now - timedelta(hours=21, minutes=57)).strftime("%Y-%m-%d %H:%M:%S"),
            ),
            (
                "demo-user/sh-cicd-demo",
                "Dependency Check",
                "run-881940",
                "ModuleNotFoundError",
                "ModuleNotFoundError: No module named 'pytest_mock'",
                "Traceback (most recent call last):\n  File 'test_runner.py', line 2\n    import pytest_mock\nModuleNotFoundError: No module named 'pytest_mock'",
                "RESOLVED",
                (now - timedelta(days=2)).strftime("%Y-%m-%d %H:%M:%S"),
                (now - timedelta(days=2, hours=-1)).strftime("%Y-%m-%d %H:%M:%S"),
            ),
            (
                "demo-user/sh-cicd-demo",
                "Docker Build & Test",
                "run-880412",
                "ZeroDivisionError",
                "ZeroDivisionError: division by zero in calculate_average",
                "File 'utils/math_helpers.py', line 12, in calculate_average\n    return total / len(items)\nZeroDivisionError: division by zero",
                "RESOLVED",
                (now - timedelta(days=3)).strftime("%Y-%m-%d %H:%M:%S"),
                (now - timedelta(days=3, hours=-1)).strftime("%Y-%m-%d %H:%M:%S"),
            )
        ]

        for repo, wf, run_id, err_type, err_msg, logs, status, c_at, r_at in seed_failures:
            cursor.execute("""
                INSERT INTO failures (repo_name, workflow_name, run_id, error_type, error_message, raw_logs, status, created_at, resolved_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (repo, wf, run_id, err_type, err_msg, logs, status, c_at, r_at))
            failure_id = cursor.lastrowid

            # Add corresponding PR
            cursor.execute("""
                INSERT INTO pull_requests (failure_id, pr_number, repo_name, branch_name, fix_description, patch_diff, reviewer_status, reviewer_confidence, test_status, status, html_url, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                failure_id,
                100 + failure_id,
                repo,
                f"sh-cicd/auto-fix-issue-{failure_id}",
                f"Auto-healed {err_type}: {err_msg[:60]}...",
                "--- a/calculator.py\n+++ b/calculator.py\n@@ -3,2 +3,2 @@\n-def add(a, b)\n+def add(a, b):",
                "APPROVED",
                98.5,
                "PASSED (100% test coverage)",
                "MERGED",
                f"https://github.com/demo-user/sh-cicd-demo/pull/{100 + failure_id}",
                r_at
            ))

            # Add sample agent logs
            cursor.execute("""
                INSERT INTO agent_logs (failure_id, agent_name, action, output_summary, timestamp)
                VALUES (?, 'Dispatcher', 'Log Analysis', 'Detected SyntaxError in calculator.py line 4. Classified as Syntax category.', ?)
            """, (failure_id, c_at))
            cursor.execute("""
                INSERT INTO agent_logs (failure_id, agent_name, action, output_summary, timestamp)
                VALUES (?, 'Context Gatherer', 'Repository Inspection', 'Fetched calculator.py, related test_calculator.py and commit history.', ?)
            """, (failure_id, c_at))
            cursor.execute("""
                INSERT INTO agent_logs (failure_id, agent_name, action, output_summary, timestamp)
                VALUES (?, 'Engineer', 'Patch Generation & Test', 'Generated corrected function header with missing colon. Pre-tests passed 5/5.', ?)
            """, (failure_id, r_at))
            cursor.execute("""
                INSERT INTO agent_logs (failure_id, agent_name, action, output_summary, timestamp)
                VALUES (?, 'Reviewer', 'Security & Quality Audit', 'Confidence 98.5%. No security hazards or scope creep. Fix Approved.', ?)
            """, (failure_id, r_at))

    conn.commit()


if __name__ == "__main__":
    init_db()
    print("SH-CICD Database initialized successfully.")
