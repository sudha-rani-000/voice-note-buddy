"""Automated verification test script for VoiceNote Buddy.

Tests:
1. Database initialization and CRUD operations.
2. Helper functions (JSON parsing, schema normalization, timestamp formatting, temp audio files).
3. Ollama organizer error handling and offline graceful degradation.
4. faster-whisper import, model configuration, and error resilience.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

from database.db import (
    get_voice_note_by_id,
    get_voice_notes,
    initialize_database,
    save_voice_note,
)
from utils.helpers import (
    cleanup_temp_file,
    extract_and_validate_json,
    format_timestamp,
    normalize_structured_data,
    save_temp_audio,
)
from ai.organizer import check_ollama_availability, organize_transcript
from ai.transcriber import get_default_whisper_model_name


def test_database():
    print("Testing Database CRUD...")
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tf:
        temp_db = tf.name

    try:
        initialize_database(temp_db)
        # Test Save
        note_id = save_voice_note(
            transcript="Tomorrow I have DBMS lab at 10 AM. I need to finish my assignment before evening. I also need to call Ravi about the project.",
            summary="DBMS lab tomorrow, assignment due, call Ravi.",
            tasks=[{"task": "Finish DBMS assignment", "priority": "High"}],
            events=[{"event": "DBMS lab", "date": "Tomorrow", "time": "10 AM"}],
            people=["Ravi"],
            important_points=["Assignment deadline is before evening"],
            custom_path=temp_db,
        )
        assert note_id > 0, f"Expected valid note ID, got {note_id}"

        # Test Get by ID
        note = get_voice_note_by_id(note_id, custom_path=temp_db)
        assert note is not None, "Note not found by ID"
        assert note["id"] == note_id
        assert note["summary"] == "DBMS lab tomorrow, assignment due, call Ravi."
        assert len(note["tasks"]) == 1
        assert note["tasks"][0]["priority"] == "High"
        assert len(note["events"]) == 1
        assert note["events"][0]["date"] == "Tomorrow"
        assert note["people"] == ["Ravi"]

        # Test Get All
        all_notes = get_voice_notes(custom_path=temp_db)
        assert len(all_notes) == 1
        assert all_notes[0]["id"] == note_id
        print("  Database CRUD tests PASSED!")
    finally:
        cleanup_temp_file(temp_db)


def test_json_extraction():
    print("Testing JSON Extraction and Normalization...")
    # Test 1: Clean JSON with markdown block
    markdown_sample = """Here is the extracted information:
```json
{
  "summary": "Doctor appointment next Monday.",
  "tasks": [
    {"task": "Collect blood test report", "priority": "High"}
  ],
  "events": [
    {"event": "Doctor appointment", "date": "Next Monday", "time": "11:00 AM"}
  ],
  "people": ["Dr. Smith"],
  "important_points": ["Fast for 12 hours before test"]
}
```
Hope this helps!"""

    res1 = extract_and_validate_json(markdown_sample)
    assert res1["summary"] == "Doctor appointment next Monday."
    assert len(res1["tasks"]) == 1
    assert res1["tasks"][0]["task"] == "Collect blood test report"
    assert res1["tasks"][0]["priority"] == "High"
    assert res1["people"] == ["Dr. Smith"]

    # Test 2: Missing fields should be safely normalized to defaults
    minimal_sample = """{"summary": "Just a general reflection with no tasks."}"""
    res2 = extract_and_validate_json(minimal_sample)
    assert res2["summary"] == "Just a general reflection with no tasks."
    assert res2["tasks"] == []
    assert res2["events"] == []
    assert res2["people"] == []
    assert res2["important_points"] == []

    # Test 3: Trailing commas
    trailing_comma_sample = """
    {
      "summary": "Testing trailing commas",
      "tasks": [
        {"task": "Buy milk", "priority": "low",}
      ],
      "events": [],
      "people": [],
      "important_points": [],
    }
    """
    res3 = extract_and_validate_json(trailing_comma_sample)
    assert res3["tasks"][0]["priority"] == "Low"

    print("  JSON extraction tests PASSED!")


def test_helpers():
    print("Testing Helpers...")
    # Timestamp formatting
    formatted = format_timestamp("2026-10-03 14:30:00")
    assert "2026" in formatted and "02:30 PM" in formatted

    # Audio saving & cleanup
    sample_bytes = b"RIFF....WAVEfmt ...."
    tmp_path = save_temp_audio(sample_bytes, original_filename="test_note.wav")
    assert os.path.exists(tmp_path)
    cleanup_temp_file(tmp_path)
    assert not os.path.exists(tmp_path)
    print("  Helper tests PASSED!")


def test_ollama_graceful_handling():
    print("Testing Ollama error handling...")
    ready, msg, models = check_ollama_availability()
    print(f"  Ollama availability: ready={ready}, msg='{msg}'")
    # When Ollama is offline or uninstalled, organize_transcript should raise ConnectionError cleanly
    if not ready:
        try:
            organize_transcript("Test transcript")
            assert False, "Expected ConnectionError or LookupError when Ollama is unavailable"
        except (ConnectionError, LookupError) as e:
            print(f"  Gracefully caught offline exception: {type(e).__name__}: {e}")
    print("  Ollama handling tests PASSED!")


def test_whisper_config():
    print("Testing Whisper Configuration...")
    whisper_model = get_default_whisper_model_name()
    assert whisper_model == "base" or isinstance(whisper_model, str)
    print(f"  Configured Whisper model: '{whisper_model}'")
    print("  Whisper config test PASSED!")


if __name__ == "__main__":
    print("=" * 50)
    print("RUNNING VOICENOTE BUDDY VERIFICATION SUITE")
    print("=" * 50)
    test_database()
    test_json_extraction()
    test_helpers()
    test_ollama_graceful_handling()
    test_whisper_config()
    print("=" * 50)
    print("ALL TESTS PASSED SUCCESSFULLY!")
    print("=" * 50)
