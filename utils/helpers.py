"""Helper utilities for VoiceNote Buddy.

Includes audio temporary file management, robust JSON extraction and normalization,
timestamp formatting, and UI styling helpers.
"""

from __future__ import annotations

import json
import os
import re
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


def save_temp_audio(file_bytes_or_buffer: Any, original_filename: Optional[str] = None) -> str:
    """Save audio bytes or Streamlit UploadedFile to a temporary file.

    Returns the path to the created temporary file.
    """
    suffix = ".wav"
    if original_filename:
        ext = Path(original_filename).suffix.lower()
        if ext in {".wav", ".mp3", ".m4a", ".ogg"}:
            suffix = ext

    # Create a named temp file
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
        if hasattr(file_bytes_or_buffer, "read"):
            temp_file.write(file_bytes_or_buffer.read())
            # Reset pointer if possible
            if hasattr(file_bytes_or_buffer, "seek"):
                file_bytes_or_buffer.seek(0)
        elif isinstance(file_bytes_or_buffer, (bytes, bytearray)):
            temp_file.write(file_bytes_or_buffer)
        else:
            raise ValueError("Unsupported audio data type provided.")
        return temp_file.name


def cleanup_temp_file(file_path: Optional[str]) -> None:
    """Safely remove a temporary file if it exists."""
    if not file_path:
        return
    try:
        p = Path(file_path)
        if p.exists() and p.is_file():
            p.unlink(missing_ok=True)
    except Exception:
        pass


def extract_and_validate_json(raw_text: str) -> Dict[str, Any]:
    """Extract and validate the structured organizer JSON from raw LLM output.

    Handles markdown fences, leading/trailing conversational text, and schema normalization.
    Raises ValueError if valid JSON cannot be found or parsed.
    """
    if not raw_text or not raw_text.strip():
        raise ValueError("LLM returned empty response.")

    text = raw_text.strip()

    # Step 1: Strip markdown code blocks if wrapped in ```json ... ``` or ``` ... ```
    fence_pattern = r"```(?:json)?\s*([\s\S]*?)\s*```"
    fence_match = re.search(fence_pattern, text, re.IGNORECASE)
    candidate_text = fence_match.group(1).strip() if fence_match else text

    # Step 2: If candidate_text isn't direct JSON, find outermost { ... }
    parsed_json: Optional[Dict[str, Any]] = None
    parse_errors = []

    # Try direct parse
    try:
        parsed = json.loads(candidate_text)
        if isinstance(parsed, dict):
            parsed_json = parsed
    except Exception as err:
        parse_errors.append(str(err))

    # If direct parse failed, scan for braces
    if parsed_json is None:
        brace_match = re.search(r"(\{[\s\S]*\})", text)
        if brace_match:
            extracted = brace_match.group(1).strip()
            # Attempt to strip trailing commas before closing braces/brackets
            cleaned = re.sub(r",\s*([\]\}])", r"\1", extracted)
            try:
                parsed = json.loads(cleaned)
                if isinstance(parsed, dict):
                    parsed_json = parsed
            except Exception as err:
                parse_errors.append(str(err))

    if parsed_json is None:
        raise ValueError(
            f"Failed to extract valid JSON from LLM output. Parsing errors: {'; '.join(parse_errors)}"
        )

    return normalize_structured_data(parsed_json)


def normalize_structured_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """Ensure the parsed dictionary conforms strictly to the expected schema."""
    # Summary
    summary = str(data.get("summary") or "").strip()

    # Tasks: list of dicts with 'task' and 'priority' ('High', 'Medium', 'Low')
    raw_tasks = data.get("tasks")
    tasks: List[Dict[str, str]] = []
    if isinstance(raw_tasks, list):
        for item in raw_tasks:
            if isinstance(item, dict):
                task_desc = str(item.get("task") or "").strip()
                priority = str(item.get("priority") or "Medium").capitalize()
                if priority not in {"High", "Medium", "Low"}:
                    priority = "Medium"
                if task_desc:
                    tasks.append({"task": task_desc, "priority": priority})
            elif isinstance(item, str) and item.strip():
                tasks.append({"task": item.strip(), "priority": "Medium"})

    # Events: list of dicts with 'event', 'date', 'time'
    raw_events = data.get("events")
    events: List[Dict[str, str]] = []
    if isinstance(raw_events, list):
        for item in raw_events:
            if isinstance(item, dict):
                event_name = str(item.get("event") or "").strip()
                date_val = str(item.get("date") or "").strip()
                time_val = str(item.get("time") or "").strip()
                if event_name:
                    events.append(
                        {
                            "event": event_name,
                            "date": date_val,
                            "time": time_val,
                        }
                    )
            elif isinstance(item, str) and item.strip():
                events.append({"event": item.strip(), "date": "", "time": ""})

    # People: list of strings
    raw_people = data.get("people")
    people: List[str] = []
    if isinstance(raw_people, list):
        for p in raw_people:
            if isinstance(p, str) and p.strip():
                people.append(p.strip())
            elif isinstance(p, dict) and "name" in p:
                people.append(str(p["name"]).strip())

    # Important Points: list of strings
    raw_points = data.get("important_points")
    important_points: List[str] = []
    if isinstance(raw_points, list):
        for pt in raw_points:
            if isinstance(pt, str) and pt.strip():
                important_points.append(pt.strip())
            elif isinstance(pt, dict) and "point" in pt:
                important_points.append(str(pt["point"]).strip())

    return {
        "summary": summary,
        "tasks": tasks,
        "events": events,
        "people": people,
        "important_points": important_points,
    }


def format_timestamp(raw_timestamp: str) -> str:
    """Format an SQLite timestamp or ISO string into a readable string."""
    if not raw_timestamp:
        return "Unknown Date"
    # Format candidates: '2026-10-03 02:45:00', '2026-10-03T02:45:00', etc.
    formats = [
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M:%S.%f",
        "%Y-%m-%d",
    ]
    cleaned = raw_timestamp.split("+")[0].split("Z")[0].strip()
    for fmt in formats:
        try:
            dt = datetime.strptime(cleaned, fmt)
            return dt.strftime("%b %d, %Y • %I:%M %p")
        except ValueError:
            continue
    return raw_timestamp
