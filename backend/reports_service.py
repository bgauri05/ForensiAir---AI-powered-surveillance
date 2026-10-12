"""
backend/reports_service.py
==========================
Database storage, schema initialization, validation, and business logic
for ForensiAIR Inspection Verification Reports.

Data tables in forensier.db:
- inspection_reports: Persists report details, status, outcome, evidence, and admin reviews.
- report_revisions: Append-only audit trail capturing full historical snapshots and actions.
"""

import os
import json
import sqlite3
import datetime
from typing import Dict, Any, List, Optional, Tuple

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "forensier.db")
if not os.path.exists(DB_PATH):
    DB_PATH = "forensier.db"


def get_db_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_reports_tables():
    """
    Safely creates the inspection_reports and report_revisions tables if they don't exist.
    Preserves all existing data in forensier.db.
    """
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS inspection_reports (
                report_id TEXT PRIMARY KEY,
                alert_id TEXT NOT NULL,
                factory_id TEXT NOT NULL,
                factory_name TEXT,
                case_id TEXT,
                inspector_id TEXT NOT NULL,
                inspector_name TEXT,
                inspection_date TEXT NOT NULL,
                checks_performed TEXT NOT NULL,
                other_checks_description TEXT,
                findings TEXT NOT NULL,
                outcome TEXT NOT NULL,
                evidence_references TEXT,
                status TEXT NOT NULL DEFAULT 'Draft',
                admin_notes TEXT,
                admin_decision TEXT,
                reviewed_by TEXT,
                reviewed_at TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                submitted_at TEXT
            );
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS report_revisions (
                revision_id INTEGER PRIMARY KEY AUTOINCREMENT,
                report_id TEXT NOT NULL,
                revision_number INTEGER NOT NULL,
                action TEXT NOT NULL,
                actor_id TEXT NOT NULL,
                actor_role TEXT,
                summary TEXT NOT NULL,
                snapshot_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (report_id) REFERENCES inspection_reports(report_id)
            );
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_reports_alert_id ON inspection_reports(alert_id);
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_reports_factory_id ON inspection_reports(factory_id);
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_reports_status ON inspection_reports(status);
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_revisions_report_id ON report_revisions(report_id);
        """)

        conn.commit()
    finally:
        conn.close()


def find_alert_details(alert_id: str) -> Optional[Dict[str, Any]]:
    """
    Looks up the alert in the database 'alerts' table, or in the V2 evaluated events.
    Returns dictionary with factory_id, factory_name, parameter, severity, alert_type if found.
    """
    alert_str = str(alert_id).strip()
    conn = get_db_connection()
    try:
        # 1. Search in forensier.db 'alerts' table (checking both integer and string id)
        row = conn.execute(
            "SELECT id, factory_id, alert_type, severity, message, timestamp, status "
            "FROM alerts WHERE id = ? OR CAST(id AS TEXT) = ?",
            (alert_str, alert_str)
        ).fetchone()

        if row:
            fid = row["factory_id"]
            # Look up factory name if possible
            f_row = conn.execute("SELECT name FROM factories WHERE factory_id = ?", (fid,)).fetchone()
            fname = f_row["name"] if f_row else f"Industrial Site {fid}"
            return {
                "alert_id": str(row["id"]),
                "factory_id": fid,
                "factory_name": fname,
                "alert_type": row["alert_type"],
                "severity": row["severity"],
                "message": row["message"],
                "timestamp": row["timestamp"],
                "source": "prototype_db_alerts"
            }
    finally:
        conn.close()

    # 2. Search in V2 evaluated events CSV
    from backend.v2_adapter import get_v2_adapter, FACTORY_NAMES
    adapter = get_v2_adapter()
    if adapter._events_df is not None and not adapter._events_df.empty:
        matching = adapter._events_df[adapter._events_df["event_id"].astype(str) == alert_str]
        if not matching.empty:
            erow = matching.iloc[0]
            fid = str(erow["factory_id"])
            fname, reg, ind = FACTORY_NAMES.get(fid, (f"Industrial Site {fid}", "Taloja", "Chemical Manufacturing"))
            return {
                "alert_id": alert_str,
                "factory_id": fid,
                "factory_name": fname,
                "alert_type": f"V2 {erow['type']} ({erow.get('anomaly_category', 'Statistical Anomaly')})",
                "severity": str(erow.get("severity", "moderate")),
                "message": f"{erow['type']} pattern detected on {erow['parameter']} ({erow.get('duration_rows', 16)} readings)",
                "timestamp": str(erow["start_dt"]),
                "source": "v2_evaluation_events"
            }

    return None


def generate_report_id() -> str:
    """Generates a sequential human-readable report ID like RPT-2026-0001"""
    now = datetime.datetime.utcnow()
    year = now.year
    conn = get_db_connection()
    try:
        count = conn.execute("SELECT COUNT(*) FROM inspection_reports").fetchone()[0]
        return f"RPT-{year}-{count + 1:04d}"
    finally:
        conn.close()


def create_report(
    alert_id: str,
    inspection_date: str,
    checks_performed: List[str],
    findings: str,
    outcome: str,
    inspector_id: str,
    inspector_name: Optional[str] = None,
    other_checks_description: Optional[str] = None,
    evidence_references: Optional[Dict[str, Any]] = None,
    case_id: Optional[str] = None,
    status: str = "Draft"
) -> Dict[str, Any]:
    """
    Creates a new inspection verification report in the database and logs revision #1.
    """
    alert_info = find_alert_details(alert_id)
    if not alert_info:
        raise ValueError(f"Alert ID '{alert_id}' does not exist in the system.")

    report_id = generate_report_id()
    now_iso = datetime.datetime.utcnow().isoformat()
    submitted_at = now_iso if status == "Submitted for Review" else None

    checks_json = json.dumps(checks_performed)
    evidence_json = json.dumps(evidence_references or {})

    conn = get_db_connection()
    try:
        conn.execute("""
            INSERT INTO inspection_reports (
                report_id, alert_id, factory_id, factory_name, case_id,
                inspector_id, inspector_name, inspection_date, checks_performed,
                other_checks_description, findings, outcome, evidence_references,
                status, created_at, updated_at, submitted_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            report_id, str(alert_info["alert_id"]), alert_info["factory_id"], alert_info["factory_name"],
            case_id, inspector_id, inspector_name or inspector_id, inspection_date,
            checks_json, other_checks_description, findings, outcome,
            evidence_json, status, now_iso, now_iso, submitted_at
        ))

        # Log Initial Revision
        snapshot = {
            "report_id": report_id,
            "alert_id": alert_info["alert_id"],
            "factory_id": alert_info["factory_id"],
            "findings": findings,
            "outcome": outcome,
            "checks_performed": checks_performed,
            "status": status
        }
        action_name = "submitted_for_review" if status == "Submitted for Review" else "created_draft"
        conn.execute("""
            INSERT INTO report_revisions (
                report_id, revision_number, action, actor_id, actor_role, summary, snapshot_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            report_id, 1, action_name, inspector_id, "inspector",
            f"Report created as {status} by {inspector_name or inspector_id}",
            json.dumps(snapshot), now_iso
        ))

        conn.commit()
    finally:
        conn.close()

    return get_report(report_id)


def update_report(
    report_id: str,
    inspection_date: Optional[str] = None,
    checks_performed: Optional[List[str]] = None,
    findings: Optional[str] = None,
    outcome: Optional[str] = None,
    other_checks_description: Optional[str] = None,
    evidence_references: Optional[Dict[str, Any]] = None,
    case_id: Optional[str] = None,
    actor_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Updates an existing report draft. Prevents silent overwrite of submitted or reviewed reports.
    """
    existing = get_report(report_id)
    if not existing:
        raise KeyError(f"Report '{report_id}' not found.")

    if existing["status"] in ["Submitted for Review", "Reviewed"]:
        raise ValueError(
            f"Cannot directly edit report '{report_id}' because its status is '{existing['status']}'. "
            "Submitted and reviewed reports are locked to protect data integrity. "
            "Request further information or create an amendment revision instead."
        )

    now_iso = datetime.datetime.utcnow().isoformat()
    conn = get_db_connection()
    try:
        new_date = inspection_date or existing["inspection_date"]
        new_checks = json.dumps(checks_performed) if checks_performed is not None else json.dumps(existing["checks_performed"])
        new_findings = findings if findings is not None else existing["findings"]
        new_outcome = outcome if outcome is not None else existing["outcome"]
        new_other = other_checks_description if other_checks_description is not None else existing["other_checks_description"]
        new_evidence = json.dumps(evidence_references) if evidence_references is not None else json.dumps(existing["evidence_references"])
        new_case_id = case_id if case_id is not None else existing["case_id"]

        conn.execute("""
            UPDATE inspection_reports SET
                inspection_date = ?,
                checks_performed = ?,
                findings = ?,
                outcome = ?,
                other_checks_description = ?,
                evidence_references = ?,
                case_id = ?,
                updated_at = ?
            WHERE report_id = ?
        """, (
            new_date, new_checks, new_findings, new_outcome,
            new_other, new_evidence, new_case_id, now_iso, report_id
        ))

        # Log Revision
        rev_count = conn.execute(
            "SELECT COUNT(*) FROM report_revisions WHERE report_id = ?", (report_id,)
        ).fetchone()[0]

        snapshot = {
            "report_id": report_id,
            "findings": new_findings,
            "outcome": new_outcome,
            "checks_performed": json.loads(new_checks),
            "status": existing["status"]
        }

        conn.execute("""
            INSERT INTO report_revisions (
                report_id, revision_number, action, actor_id, actor_role, summary, snapshot_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            report_id, rev_count + 1, "updated_draft", actor_id or existing["inspector_id"], "inspector",
            f"Draft updated by {actor_id or existing['inspector_id']}",
            json.dumps(snapshot), now_iso
        ))

        conn.commit()
    finally:
        conn.close()

    return get_report(report_id)


def submit_report(report_id: str, actor_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Submits a draft report for administrator review.
    Validates required fields before submission.
    """
    existing = get_report(report_id)
    if not existing:
        raise KeyError(f"Report '{report_id}' not found.")

    if existing["status"] == "Submitted for Review":
        return existing
    if existing["status"] == "Reviewed":
        raise ValueError(f"Report '{report_id}' has already been reviewed and finalized.")

    # Validation
    if not existing["findings"] or len(existing["findings"].strip()) < 10:
        raise ValueError("Inspection findings must contain at least 10 characters before submission.")
    if not existing["checks_performed"] or len(existing["checks_performed"]) == 0:
        raise ValueError("At least one inspection check must be selected before submission.")
    if not existing["outcome"]:
        raise ValueError("An inspection outcome must be selected before submission.")

    now_iso = datetime.datetime.utcnow().isoformat()
    conn = get_db_connection()
    try:
        conn.execute("""
            UPDATE inspection_reports SET
                status = 'Submitted for Review',
                submitted_at = ?,
                updated_at = ?
            WHERE report_id = ?
        """, (now_iso, now_iso, report_id))

        rev_count = conn.execute(
            "SELECT COUNT(*) FROM report_revisions WHERE report_id = ?", (report_id,)
        ).fetchone()[0]

        conn.execute("""
            INSERT INTO report_revisions (
                report_id, revision_number, action, actor_id, actor_role, summary, snapshot_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            report_id, rev_count + 1, "submitted_for_review", actor_id or existing["inspector_id"], "inspector",
            f"Report submitted for administrator review by {actor_id or existing['inspector_id']}",
            json.dumps({"report_id": report_id, "status": "Submitted for Review"}), now_iso
        ))

        conn.commit()
    finally:
        conn.close()

    return get_report(report_id)


def review_report(
    report_id: str,
    decision: str,
    admin_notes: str,
    admin_id: str
) -> Dict[str, Any]:
    """
    Records an administrator's review decision ('Reviewed' or 'Further Information Required').
    """
    existing = get_report(report_id)
    if not existing:
        raise KeyError(f"Report '{report_id}' not found.")

    valid_decisions = ["Reviewed", "Further Information Required"]
    if decision not in valid_decisions:
        raise ValueError(f"Invalid review decision '{decision}'. Must be one of {valid_decisions}.")

    if not admin_notes or not admin_notes.strip():
        raise ValueError("Administrator review notes are required.")

    now_iso = datetime.datetime.utcnow().isoformat()
    conn = get_db_connection()
    try:
        conn.execute("""
            UPDATE inspection_reports SET
                status = ?,
                admin_notes = ?,
                admin_decision = ?,
                reviewed_by = ?,
                reviewed_at = ?,
                updated_at = ?
            WHERE report_id = ?
        """, (decision, admin_notes, decision, admin_id, now_iso, now_iso, report_id))

        rev_count = conn.execute(
            "SELECT COUNT(*) FROM report_revisions WHERE report_id = ?", (report_id,)
        ).fetchone()[0]

        action_name = "admin_reviewed" if decision == "Reviewed" else "info_requested"
        summary_text = (
            f"Report marked as '{decision}' by Admin ({admin_id}). Notes: {admin_notes[:60]}"
            if len(admin_notes) <= 60 else f"Report marked as '{decision}' by Admin ({admin_id}). Notes: {admin_notes[:60]}..."
        )

        conn.execute("""
            INSERT INTO report_revisions (
                report_id, revision_number, action, actor_id, actor_role, summary, snapshot_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            report_id, rev_count + 1, action_name, admin_id, "admin",
            summary_text,
            json.dumps({"report_id": report_id, "status": decision, "admin_notes": admin_notes}), now_iso
        ))

        conn.commit()
    finally:
        conn.close()

    return get_report(report_id)


def get_report(report_id: str) -> Optional[Dict[str, Any]]:
    """Retrieves a single report with parsed JSON fields and revision history."""
    conn = get_db_connection()
    try:
        row = conn.execute(
            "SELECT * FROM inspection_reports WHERE report_id = ?", (report_id,)
        ).fetchone()

        if not row:
            return None

        # Revisions
        rev_rows = conn.execute(
            "SELECT * FROM report_revisions WHERE report_id = ? ORDER BY revision_number ASC",
            (report_id,)
        ).fetchall()

        revisions = []
        for r in rev_rows:
            try:
                snap = json.loads(r["snapshot_json"])
            except Exception:
                snap = {}
            revisions.append({
                "revision_id": r["revision_id"],
                "revision_number": r["revision_number"],
                "action": r["action"],
                "actor_id": r["actor_id"],
                "actor_role": r["actor_role"],
                "summary": r["summary"],
                "snapshot": snap,
                "created_at": r["created_at"]
            })

        # Alert details lookup
        alert_info = find_alert_details(row["alert_id"])

        return {
            "report_id": row["report_id"],
            "alert_id": row["alert_id"],
            "factory_id": row["factory_id"],
            "factory_name": row["factory_name"],
            "case_id": row["case_id"],
            "inspector_id": row["inspector_id"],
            "inspector_name": row["inspector_name"],
            "inspection_date": row["inspection_date"],
            "checks_performed": json.loads(row["checks_performed"]) if row["checks_performed"] else [],
            "other_checks_description": row["other_checks_description"],
            "findings": row["findings"],
            "outcome": row["outcome"],
            "evidence_references": json.loads(row["evidence_references"]) if row["evidence_references"] else {},
            "status": row["status"],
            "admin_notes": row["admin_notes"],
            "admin_decision": row["admin_decision"],
            "reviewed_by": row["reviewed_by"],
            "reviewed_at": row["reviewed_at"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
            "submitted_at": row["submitted_at"],
            "revisions": revisions,
            "linked_alert": alert_info
        }
    finally:
        conn.close()


def list_reports(
    status: Optional[str] = None,
    alert_id: Optional[str] = None,
    factory_id: Optional[str] = None,
    limit: int = 50,
    offset: int = 0
) -> Dict[str, Any]:
    """Lists inspection reports with optional filtering."""
    conn = get_db_connection()
    try:
        query = "SELECT * FROM inspection_reports WHERE 1=1"
        params = []

        if status and status.upper() != "ALL":
            query += " AND status = ?"
            params.append(status)

        if alert_id:
            query += " AND alert_id = ?"
            params.append(str(alert_id))

        if factory_id:
            query += " AND factory_id = ?"
            params.append(str(factory_id))

        count_query = query.replace("SELECT *", "SELECT COUNT(*)")
        total = conn.execute(count_query, params).fetchone()[0]

        query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        rows = conn.execute(query, params).fetchall()
        reports = []
        for row in rows:
            reports.append({
                "report_id": row["report_id"],
                "alert_id": row["alert_id"],
                "factory_id": row["factory_id"],
                "factory_name": row["factory_name"],
                "case_id": row["case_id"],
                "inspector_id": row["inspector_id"],
                "inspector_name": row["inspector_name"],
                "inspection_date": row["inspection_date"],
                "checks_performed": json.loads(row["checks_performed"]) if row["checks_performed"] else [],
                "other_checks_description": row["other_checks_description"],
                "findings": row["findings"],
                "outcome": row["outcome"],
                "evidence_references": json.loads(row["evidence_references"]) if row["evidence_references"] else {},
                "status": row["status"],
                "admin_notes": row["admin_notes"],
                "admin_decision": row["admin_decision"],
                "reviewed_by": row["reviewed_by"],
                "reviewed_at": row["reviewed_at"],
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
                "submitted_at": row["submitted_at"]
            })

        return {"reports": reports, "total": total, "limit": limit, "offset": offset}
    finally:
        conn.close()


def get_alert_report_statuses() -> Dict[str, Dict[str, Any]]:
    """
    Returns a dictionary mapping alert_id -> {status, report_id, updated_at}
    for quickly determining report badge state for each alert on the frontend.
    """
    conn = get_db_connection()
    try:
        rows = conn.execute(
            "SELECT alert_id, report_id, status, updated_at, inspection_date FROM inspection_reports"
        ).fetchall()
        res = {}
        for r in rows:
            res[str(r["alert_id"])] = {
                "report_id": r["report_id"],
                "status": r["status"],
                "updated_at": r["updated_at"],
                "inspection_date": r["inspection_date"]
            }
        return res
    finally:
        conn.close()
