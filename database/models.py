import sqlite3
from datetime import datetime
from .database import get_db_connection


# ==========================================
# FAILURES MODEL
# ==========================================
def get_failures(limit=50):
    conn = get_db_connection()
    failures = conn.execute(
        "SELECT * FROM failures ORDER BY created_at DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return [dict(f) for f in failures]


def get_failure_by_id(failure_id):
    conn = get_db_connection()
    failure = conn.execute(
        "SELECT * FROM failures WHERE id = ?", (failure_id,)
    ).fetchone()
    conn.close()
    return dict(failure) if failure else None


def create_failure(repo_name, workflow_name, run_id, error_type, error_message, raw_logs, status="PENDING"):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO failures (repo_name, workflow_name, run_id, error_type, error_message, raw_logs, status, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        repo_name, workflow_name, run_id, error_type, error_message, raw_logs, status,
        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ))
    failure_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return failure_id


def update_failure_status(failure_id, status, resolved_at=None):
    conn = get_db_connection()
    if resolved_at:
        conn.execute(
            "UPDATE failures SET status = ?, resolved_at = ? WHERE id = ?",
            (status, resolved_at, failure_id)
        )
    else:
        conn.execute(
            "UPDATE failures SET status = ? WHERE id = ?",
            (status, failure_id)
        )
    conn.commit()
    conn.close()


# ==========================================
# AGENTS MODEL
# ==========================================
def get_agents():
    conn = get_db_connection()
    agents = conn.execute("SELECT * FROM agents ORDER BY id ASC").fetchall()
    conn.close()
    return [dict(a) for a in agents]


def get_agent_by_name(agent_name):
    conn = get_db_connection()
    agent = conn.execute("SELECT * FROM agents WHERE agent_name = ?", (agent_name,)).fetchone()
    conn.close()
    return dict(agent) if agent else None


def update_agent_status(agent_name, status, current_task=None, increment_completed=False, is_success=True, latency_ms=None):
    conn = get_db_connection()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cursor = conn.cursor()
    current = cursor.execute("SELECT * FROM agents WHERE agent_name = ?", (agent_name,)).fetchone()
    if not current:
        conn.close()
        return

    completed_tasks = current["completed_tasks"]
    successful_fixes = current["successful_fixes"]
    failed_tasks = current["failed_tasks"]
    avg_latency = current["avg_latency_ms"]

    if increment_completed:
        completed_tasks += 1
        if is_success:
            successful_fixes += 1
        else:
            failed_tasks += 1
        if latency_ms is not None and latency_ms > 0:
            avg_latency = round((avg_latency * (completed_tasks - 1) + latency_ms) / completed_tasks, 1)

    task_desc = current_task if current_task is not None else current["current_task"]

    cursor.execute("""
        UPDATE agents
        SET status = ?, current_task = ?, completed_tasks = ?, successful_fixes = ?,
            failed_tasks = ?, avg_latency_ms = ?, last_active = ?
        WHERE agent_name = ?
    """, (status, task_desc, completed_tasks, successful_fixes, failed_tasks, avg_latency, now_str, agent_name))

    conn.commit()
    conn.close()


# ==========================================
# PULL REQUESTS MODEL
# ==========================================
def create_pull_request(failure_id, pr_number, repo_name, branch_name, fix_description, patch_diff,
                        reviewer_status="APPROVED", reviewer_confidence=95.0, test_status="PASSED",
                        status="OPEN", html_url=""):
    conn = get_db_connection()
    cursor = conn.cursor()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("""
        INSERT INTO pull_requests (
            failure_id, pr_number, repo_name, branch_name, fix_description,
            patch_diff, reviewer_status, reviewer_confidence, test_status, status, html_url, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        failure_id, pr_number, repo_name, branch_name, fix_description,
        patch_diff, reviewer_status, reviewer_confidence, test_status, status, html_url, now_str
    ))
    pr_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return pr_id


def get_pull_requests(limit=50):
    conn = get_db_connection()
    prs = conn.execute("""
        SELECT pr.*, f.workflow_name, f.error_type
        FROM pull_requests pr
        LEFT JOIN failures f ON pr.failure_id = f.id
        ORDER BY pr.created_at DESC LIMIT ?
    """, (limit,)).fetchall()
    conn.close()
    return [dict(p) for p in prs]


def get_pull_request_by_id(pr_id):
    conn = get_db_connection()
    pr = conn.execute("SELECT * FROM pull_requests WHERE id = ?", (pr_id,)).fetchone()
    conn.close()
    return dict(pr) if pr else None


# ==========================================
# AGENT LOGS MODEL
# ==========================================
def create_agent_log(failure_id, agent_name, action, output_summary):
    conn = get_db_connection()
    cursor = conn.cursor()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("""
        INSERT INTO agent_logs (failure_id, agent_name, action, output_summary, timestamp)
        VALUES (?, ?, ?, ?, ?)
    """, (failure_id, agent_name, action, output_summary, now_str))
    log_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return log_id


def get_agent_logs(failure_id=None, limit=100):
    conn = get_db_connection()
    if failure_id:
        logs = conn.execute(
            "SELECT * FROM agent_logs WHERE failure_id = ? ORDER BY timestamp DESC, id DESC LIMIT ?",
            (failure_id, limit)
        ).fetchall()
    else:
        logs = conn.execute(
            "SELECT * FROM agent_logs ORDER BY timestamp DESC, id DESC LIMIT ?",
            (limit,)
        ).fetchall()
    conn.close()
    return [dict(l) for l in logs]


# ==========================================
# SETTINGS MODEL
# ==========================================
def get_settings():
    conn = get_db_connection()
    settings = conn.execute("SELECT * FROM settings ORDER BY id ASC LIMIT 1").fetchone()
    conn.close()
    if settings:
        return dict(settings)
    return {
        "github_token": "",
        "target_repo": "demo-user/sh-cicd-demo",
        "webhook_secret": "demo_webhook_secret",
        "ai_provider": "demo",
        "ai_api_key": "",
        "ai_model_name": "gemini-1.5-flash",
        "demo_mode": 1,
        "auto_pr_enabled": 1,
        "min_confidence_threshold": 80.0
    }


def update_settings(data):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE settings SET
            github_token = ?,
            target_repo = ?,
            webhook_secret = ?,
            ai_provider = ?,
            ai_api_key = ?,
            ai_model_name = ?,
            demo_mode = ?,
            auto_pr_enabled = ?,
            min_confidence_threshold = ?
        WHERE id = (SELECT id FROM settings LIMIT 1)
    """, (
        data.get("github_token", ""),
        data.get("target_repo", "demo-user/sh-cicd-demo"),
        data.get("webhook_secret", ""),
        data.get("ai_provider", "demo"),
        data.get("ai_api_key", ""),
        data.get("ai_model_name", "gemini-1.5-flash"),
        1 if data.get("demo_mode") in [1, True, "1", "true", "on"] else 0,
        1 if data.get("auto_pr_enabled") in [1, True, "1", "true", "on"] else 0,
        float(data.get("min_confidence_threshold", 80.0))
    ))
    conn.commit()
    conn.close()


# ==========================================
# DASHBOARD STATS AGGREGATOR
# ==========================================
def get_stats():
    conn = get_db_connection()

    total_failures = conn.execute("SELECT COUNT(*) FROM failures").fetchone()[0]
    fixed_failures = conn.execute("SELECT COUNT(*) FROM failures WHERE status = 'RESOLVED'").fetchone()[0]
    open_failures = conn.execute("SELECT COUNT(*) FROM failures WHERE status IN ('PENDING', 'IN_PROGRESS')").fetchone()[0]
    total_prs = conn.execute("SELECT COUNT(*) FROM pull_requests").fetchone()[0]

    # Categories breakdown
    categories_raw = conn.execute(
        "SELECT error_type, COUNT(*) as count FROM failures GROUP BY error_type ORDER BY count DESC"
    ).fetchall()
    categories = {row["error_type"]: row["count"] for row in categories_raw}

    # Success rate
    success_rate = round((fixed_failures / total_failures * 100) if total_failures > 0 else 100.0, 1)

    # Status breakdown
    statuses_raw = conn.execute(
        "SELECT status, COUNT(*) as count FROM failures GROUP BY status"
    ).fetchall()
    status_counts = {row["status"]: row["count"] for row in statuses_raw}

    conn.close()

    return {
        "total_failures": total_failures,
        "fixed_failures": fixed_failures,
        "open_failures": open_failures,
        "total_prs": total_prs,
        "success_rate": success_rate,
        "categories": categories,
        "status_counts": status_counts
    }
