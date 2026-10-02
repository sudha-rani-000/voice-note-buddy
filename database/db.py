"""Database module for VoiceNote Buddy.

Manages SQLite persistence for transcribed voice notes, extracted tasks,
events, participants, summaries, and key points.
"""

from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional

# Base directory for the project
BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_DB_PATH = BASE_DIR / "data" / "voice_notes.db"


def get_db_path(custom_path: Optional[str | Path] = None) -> Path:
    """Return the database path, creating parent directories if needed."""
    path = Path(custom_path) if custom_path else DEFAULT_DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def get_connection(custom_path: Optional[str | Path] = None) -> sqlite3.Connection:
    """Create and return a database connection with row factory configured."""
    db_path = get_db_path(custom_path)
    conn = sqlite3.connect(str(db_path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def initialize_database(custom_path: Optional[str | Path] = None) -> None:
    """Initialize the SQLite database schema if it doesn't already exist."""
    db_path = get_db_path(custom_path)
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS voice_notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                transcript TEXT NOT NULL,
                summary TEXT DEFAULT '',
                tasks TEXT DEFAULT '[]',
                events TEXT DEFAULT '[]',
                people TEXT DEFAULT '[]',
                important_points TEXT DEFAULT '[]'
            )
            """
        )
        conn.commit()


def _serialize_field(val: Any) -> str:
    """Safely serialize an object to JSON string."""
    if isinstance(val, str):
        # Already a string; verify if it's valid json or plain text
        try:
            # Ensure it is json-parseable or wrap it
            json.loads(val)
            return val
        except Exception:
            return json.dumps(val)
    if val is None:
        return json.dumps([])
    return json.dumps(val, ensure_ascii=False)


def _deserialize_field(raw: Optional[str], default_val: Any = None) -> Any:
    """Safely deserialize a JSON string from SQLite."""
    if default_val is None:
        default_val = []
    if not raw:
        return default_val
    try:
        return json.loads(raw)
    except Exception:
        return default_val


def save_voice_note(
    transcript: str,
    summary: str = "",
    tasks: Optional[List[Dict[str, Any]] | str] = None,
    events: Optional[List[Dict[str, Any]] | str] = None,
    people: Optional[List[str] | str] = None,
    important_points: Optional[List[str] | str] = None,
    custom_path: Optional[str | Path] = None,
) -> int:
    """Save a processed voice note to SQLite and return the inserted note id."""
    initialize_database(custom_path)

    tasks_json = _serialize_field(tasks or [])
    events_json = _serialize_field(events or [])
    people_json = _serialize_field(people or [])
    points_json = _serialize_field(important_points or [])

    with get_connection(custom_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO voice_notes (
                transcript, summary, tasks, events, people, important_points
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                transcript.strip(),
                summary.strip(),
                tasks_json,
                events_json,
                people_json,
                points_json,
            ),
        )
        conn.commit()
        return int(cursor.lastrowid)


def _row_to_dict(row: sqlite3.Row) -> Dict[str, Any]:
    """Convert an SQLite row to a dictionary with deserialized JSON lists."""
    return {
        "id": row["id"],
        "created_at": row["created_at"],
        "transcript": row["transcript"],
        "summary": row["summary"] or "",
        "tasks": _deserialize_field(row["tasks"], default_val=[]),
        "events": _deserialize_field(row["events"], default_val=[]),
        "people": _deserialize_field(row["people"], default_val=[]),
        "important_points": _deserialize_field(row["important_points"], default_val=[]),
    }


def get_voice_notes(custom_path: Optional[str | Path] = None) -> List[Dict[str, Any]]:
    """Retrieve all voice notes ordered by newest first."""
    initialize_database(custom_path)
    with get_connection(custom_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, created_at, transcript, summary, tasks, events, people, important_points
            FROM voice_notes
            ORDER BY datetime(created_at) DESC, id DESC
            """
        )
        rows = cursor.fetchall()
        return [_row_to_dict(row) for row in rows]


def get_voice_note_by_id(
    note_id: int, custom_path: Optional[str | Path] = None
) -> Optional[Dict[str, Any]]:
    """Retrieve a single voice note by ID with deserialized JSON fields."""
    initialize_database(custom_path)
    with get_connection(custom_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, created_at, transcript, summary, tasks, events, people, important_points
            FROM voice_notes
            WHERE id = ?
            """,
            (note_id,),
        )
        row = cursor.fetchone()
        if row is None:
            return None
        return _row_to_dict(row)
