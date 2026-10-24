"""Account, workspace membership, and persistent-session operations."""
from __future__ import annotations

import re
import sqlite3
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from .security import hash_password, issue_token, token_digest, verify_password

SESSION_HOURS = 12
USERNAME_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{2,31}$")


def validate_credentials(username: str, password: str) -> tuple[str, str]:
    username = username.strip()
    if not USERNAME_PATTERN.fullmatch(username):
        raise ValueError("Username must be 3–32 characters using letters, numbers, dot, underscore, or hyphen.")
    if not isinstance(password, str) or not 10 <= len(password) <= 128:
        raise ValueError("Password must be between 10 and 128 characters.")
    return username, password


def create_account(db: sqlite3.Connection, username: str, password: str, *, role: str = "owner") -> dict:
    username, password = validate_credentials(username, password)
    user_id, workspace_id = uuid4().hex, uuid4().hex
    created = datetime.now(timezone.utc).isoformat()
    db.execute("INSERT INTO users(id,username,password_hash,created_at) VALUES(?,?,?,?)",
               (user_id, username, hash_password(password), created))
    workspace_name = f"{username}'s workspace"
    db.execute("INSERT INTO workspaces(id,name,created_at) VALUES(?,?,?)", (workspace_id, workspace_name, created))
    db.execute("INSERT INTO memberships(user_id,workspace_id,role,created_at) VALUES(?,?,?,?)",
               (user_id, workspace_id, role, created))
    return {"id": user_id, "username": username, "workspace_id": workspace_id,
            "workspace_name": workspace_name, "role": role}


def ensure_demo_account(db: sqlite3.Connection, password: str) -> None:
    found = db.execute("SELECT id FROM users WHERE username='demo' COLLATE NOCASE").fetchone()
    if found:
        demo_id = found["id"]
        memberships = db.execute("""SELECT w.id,w.name FROM memberships m JOIN workspaces w
            ON w.id=m.workspace_id WHERE m.user_id=? ORDER BY m.created_at LIMIT 1""", (demo_id,)).fetchone()
        if not memberships:
            workspace_id, created = uuid4().hex, datetime.now(timezone.utc).isoformat()
            db.execute("INSERT INTO workspaces(id,name,created_at) VALUES(?,?,?)", (workspace_id, "Demo workspace", created))
            db.execute("INSERT INTO memberships(user_id,workspace_id,role,created_at) VALUES(?,?,?,?)",
                       (demo_id, workspace_id, "owner", created))
            memberships = {"id": workspace_id}
        db.execute("UPDATE datasets SET workspace_id=? WHERE workspace_id IS NULL", (memberships["id"],))
        return
    demo = create_account(db, "demo", password)
    db.execute("UPDATE workspaces SET name='Demo workspace' WHERE id=?", (demo["workspace_id"],))
    db.execute("UPDATE datasets SET workspace_id=? WHERE workspace_id IS NULL", (demo["workspace_id"],))


def authenticate(db: sqlite3.Connection, username: str, password: str):
    row = db.execute("SELECT id,username,password_hash FROM users WHERE username=? COLLATE NOCASE",
                     (username.strip(),)).fetchone()
    if not row or not verify_password(password, row["password_hash"]):
        return None
    return dict(row)


def create_session(db: sqlite3.Connection, user_id: str) -> tuple[str, str, str]:
    membership = db.execute("""SELECT w.id FROM memberships m JOIN workspaces w ON w.id=m.workspace_id
        WHERE m.user_id=? ORDER BY m.created_at LIMIT 1""", (user_id,)).fetchone()
    if not membership:
        raise ValueError("Account has no workspace membership.")
    token, digest = issue_token()
    created = datetime.now(timezone.utc)
    expires = created + timedelta(hours=SESSION_HOURS)
    db.execute("""INSERT INTO sessions(token_hash,user_id,active_workspace_id,created_at,expires_at)
        VALUES(?,?,?,?,?)""", (digest, user_id, membership["id"], created.isoformat(), expires.isoformat()))
    return token, membership["id"], expires.isoformat()


def resolve_session(db: sqlite3.Connection, token: str | None):
    if not token:
        return None
    digest = token_digest(token)
    row = db.execute("""SELECT s.token_hash,s.user_id,s.active_workspace_id,s.expires_at,
        u.username,m.role,w.name AS workspace_name FROM sessions s JOIN users u ON u.id=s.user_id
        JOIN memberships m ON m.user_id=s.user_id AND m.workspace_id=s.active_workspace_id
        JOIN workspaces w ON w.id=s.active_workspace_id WHERE s.token_hash=?""", (digest,)).fetchone()
    if not row:
        return None
    if row["expires_at"] <= datetime.now(timezone.utc).isoformat():
        db.execute("DELETE FROM sessions WHERE token_hash=?", (digest,))
        return None
    return dict(row)


def change_workspace(db: sqlite3.Connection, session_hash: str, user_id: str, workspace_id: str) -> bool:
    membership = db.execute("SELECT 1 FROM memberships WHERE user_id=? AND workspace_id=?",
                            (user_id, workspace_id)).fetchone()
    if not membership:
        return False
    db.execute("UPDATE sessions SET active_workspace_id=? WHERE token_hash=? AND user_id=?",
               (workspace_id, session_hash, user_id))
    return True
