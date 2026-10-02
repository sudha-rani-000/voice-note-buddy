"""VoiceNote Buddy - Main Streamlit Application.

An open-source, 100% local AI assistant that turns messy voice notes into organized actions.
Powered by faster-whisper for local transcription, Ollama for local LLM extraction,
and SQLite for persistent history.
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

import streamlit as st
from dotenv import load_dotenv

from ai.organizer import (
    check_ollama_availability,
    get_default_ollama_model_name,
    organize_transcript,
)
from ai.transcriber import get_default_whisper_model_name, transcribe_audio
from database.db import (
    get_voice_note_by_id,
    get_voice_notes,
    initialize_database,
    save_voice_note,
)
from utils.helpers import format_timestamp

# Load environment configuration
load_dotenv()

# Page configuration
st.set_page_config(
    page_title="VoiceNote Buddy",
    page_icon="🎙️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom styling for a clean, modern productivity interface
st.markdown(
    """
    <style>
    /* Card styling */
    .note-card {
        background-color: var(--secondary-background-color);
        padding: 1.2rem;
        border-radius: 10px;
        margin-bottom: 1rem;
        border: 1px solid rgba(128, 128, 128, 0.15);
    }
    .badge-priority-high {
        background-color: #fee2e2;
        color: #991b1b;
        padding: 0.2rem 0.6rem;
        border-radius: 12px;
        font-weight: 600;
        font-size: 0.8rem;
    }
    .badge-priority-medium {
        background-color: #fef3c7;
        color: #92400e;
        padding: 0.2rem 0.6rem;
        border-radius: 12px;
        font-weight: 600;
        font-size: 0.8rem;
    }
    .badge-priority-low {
        background-color: #e0f2fe;
        color: #075985;
        padding: 0.2rem 0.6rem;
        border-radius: 12px;
        font-weight: 600;
        font-size: 0.8rem;
    }
    .tag-person {
        display: inline-block;
        background-color: var(--secondary-background-color);
        border: 1px solid rgba(128, 128, 128, 0.3);
        padding: 0.25rem 0.75rem;
        border-radius: 16px;
        margin-right: 0.4rem;
        margin-bottom: 0.4rem;
        font-size: 0.9rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def render_priority_badge(priority: str) -> str:
    """Return HTML badge corresponding to task priority."""
    p = str(priority).capitalize()
    if p == "High":
        return '<span class="badge-priority-high">High</span>'
    elif p == "Low":
        return '<span class="badge-priority-low">Low</span>'
    return '<span class="badge-priority-medium">Medium</span>'


def display_structured_note(note_data: Dict[str, Any], show_header: bool = True) -> None:
    """Render the organized voice note sections (Summary, Tasks, Events, People, Points, Transcript)."""
    if show_header:
        st.write("---")

    # 1. AI Summary
    st.subheader("AI Summary")
    summary_text = note_data.get("summary") or "No summary available."
    st.info(summary_text)

    # 2-column layout for Tasks and Events
    col_tasks, col_events = st.columns([1, 1])

    # 2. Tasks
    with col_tasks:
        st.subheader("Tasks")
        tasks = note_data.get("tasks") or []
        if tasks:
            for item in tasks:
                task_desc = item.get("task", "") if isinstance(item, dict) else str(item)
                priority = item.get("priority", "Medium") if isinstance(item, dict) else "Medium"
                badge = render_priority_badge(priority)
                st.markdown(
                    f"- {badge} **{task_desc}**",
                    unsafe_allow_html=True,
                )
        else:
            st.caption("No actionable tasks identified in this voice note.")

    # 3. Important Events
    with col_events:
        st.subheader("Important Events")
        events = note_data.get("events") or []
        if events:
            for ev in events:
                if isinstance(ev, dict):
                    event_name = ev.get("event", "Event")
                    date_val = ev.get("date", "")
                    time_val = ev.get("time", "")
                else:
                    event_name = str(ev)
                    date_val = ""
                    time_val = ""

                meta_parts = []
                if date_val:
                    meta_parts.append(f"📅 {date_val}")
                if time_val:
                    meta_parts.append(f"⏰ {time_val}")
                meta_str = f" ({' • '.join(meta_parts)})" if meta_parts else ""

                st.markdown(f"- **{event_name}**{meta_str}")
        else:
            st.caption("No specific events or appointments identified.")

    # 2-column layout for People and Important Points
    col_people, col_points = st.columns([1, 1])

    # 4. People Mentioned
    with col_people:
        st.subheader("People Mentioned")
        people = note_data.get("people") or []
        if people:
            people_html = "".join(f'<span class="tag-person">👤 {person}</span>' for person in people)
            st.markdown(people_html, unsafe_allow_html=True)
        else:
            st.caption("No people mentioned in this voice note.")

    # 5. Important Points
    with col_points:
        st.subheader("Important Points")
        points = note_data.get("important_points") or []
        if points:
            for pt in points:
                st.markdown(f"- {pt}")
        else:
            st.caption("No additional key points extracted.")

    # 6. Full Transcript
    st.write("")
    transcript = note_data.get("transcript", "")
    with st.expander("View Transcript", expanded=False):
        if transcript:
            st.text_area(
                "Original Audio Transcript",
                value=transcript,
                height=160,
                disabled=True,
                label_visibility="collapsed",
            )
        else:
            st.caption("Transcript is empty.")


def main() -> None:
    """Main application loop."""
    # Ensure database is initialized on startup
    initialize_database()

    # Session state initialization
    if "selected_note_id" not in st.session_state:
        st.session_state["selected_note_id"] = None
    if "current_processed_note" not in st.session_state:
        st.session_state["current_processed_note"] = None

    # Load configuration
    whisper_model = get_default_whisper_model_name()
    ollama_model = get_default_ollama_model_name()

    # ----------------------------------------------------
    # SIDEBAR: HISTORY & LOCAL AI STATUS
    # ----------------------------------------------------
    with st.sidebar:
        st.title("Voice Note History")

        if st.button("➕ New Voice Note", use_container_width=True, type="secondary"):
            st.session_state["selected_note_id"] = None
            st.session_state["current_processed_note"] = None
            st.rerun()

        st.markdown("---")

        notes = get_voice_notes()
        if not notes:
            st.caption("No saved voice notes yet. Record or upload one to get started!")
        else:
            for note in notes:
                note_id = note["id"]
                created_str = format_timestamp(note["created_at"])
                summary_preview = note.get("summary") or note.get("transcript", "")
                summary_preview = (
                    summary_preview[:40] + "..."
                    if len(summary_preview) > 40
                    else summary_preview
                )

                btn_label = f"🎙️ {created_str}\n{summary_preview}"
                btn_type = "primary" if st.session_state["selected_note_id"] == note_id else "secondary"

                if st.button(
                    btn_label,
                    key=f"note_btn_{note_id}",
                    use_container_width=True,
                    type=btn_type,
                ):
                    st.session_state["selected_note_id"] = note_id
                    st.session_state["current_processed_note"] = None
                    st.rerun()

        # Engine Status in Sidebar
        st.markdown("---")
        st.markdown("#### ⚙️ Local AI Engine")
        st.caption(f"**Whisper Model:** `{whisper_model}`")
        st.caption(f"**Ollama Model:** `{ollama_model}`")

        is_ollama_ready, ollama_status_msg, _ = check_ollama_availability(ollama_model)
        if is_ollama_ready:
            st.success("🟢 Ollama Connected", icon="✅")
        else:
            st.warning("⚠️ Ollama Not Ready", icon="⚠️")
            st.caption(ollama_status_msg)

    # ----------------------------------------------------
    # MAIN CONTENT AREA
    # ----------------------------------------------------
    st.title("VoiceNote Buddy")
    st.subheader("Turn messy voice notes into organized actions.")
    st.caption(
        "Record or upload a voice note. VoiceNote Buddy uses local AI to transcribe your voice "
        "and organize the important information."
    )

    # If the user selected a past note from history:
    if st.session_state["selected_note_id"] is not None:
        selected_id = st.session_state["selected_note_id"]
        saved_note = get_voice_note_by_id(selected_id)
        if saved_note:
            col_back, col_title = st.columns([1, 5])
            with col_back:
                if st.button("← Back to Record", key="back_to_new"):
                    st.session_state["selected_note_id"] = None
                    st.rerun()
            with col_title:
                st.markdown(
                    f"**Viewing Saved Note** from `{format_timestamp(saved_note['created_at'])}`"
                )

            display_structured_note(saved_note, show_header=False)
            return

    # If the user recently processed a note in this session, show it
    if st.session_state["current_processed_note"]:
        st.success("Voice note successfully processed and saved to local history!")
        display_structured_note(st.session_state["current_processed_note"], show_header=False)
        st.write("---")
        if st.button("Process Another Voice Note", type="secondary"):
            st.session_state["current_processed_note"] = None
            st.rerun()
        return

    # Recording / Uploading Section
    st.write("---")
    input_tab_record, input_tab_upload = st.tabs(
        ["🎙️ Record Voice Note", "📁 Upload Voice Note"]
    )

    selected_audio = None
    audio_source_label = ""

    with input_tab_record:
        if hasattr(st, "audio_input"):
            recorded_audio = st.audio_input(
                "Click the microphone to record your voice note:"
            )
            if recorded_audio:
                selected_audio = recorded_audio
                audio_source_label = "Recorded Voice Note"
        else:
            st.info(
                "Microphone recording requires Streamlit >= 1.37.0. "
                "You can upload your audio recording in the 'Upload Voice Note' tab."
            )

    with input_tab_upload:
        uploaded_audio = st.file_uploader(
            "Upload an audio file (WAV, MP3, M4A, OGG):",
            type=["wav", "mp3", "m4a", "ogg"],
            help="Choose a pre-recorded voice note from your device.",
        )
        if uploaded_audio:
            selected_audio = uploaded_audio
            audio_source_label = f"Uploaded File: {uploaded_audio.name}"

    # If audio is present (either recorded or uploaded)
    if selected_audio is not None:
        st.write("")
        st.markdown(f"##### Preview {audio_source_label}")
        st.audio(selected_audio)

        col_proc, _ = st.columns([1, 2])
        with col_proc:
            process_clicked = st.button(
                "Process Voice Note",
                type="primary",
                use_container_width=True,
            )

        if process_clicked:
            # Step 1: Pre-flight Ollama checks
            is_ready, status_msg, _ = check_ollama_availability(ollama_model)
            if not is_ready:
                if "not running" in status_msg.lower():
                    st.error("Ollama is not running. Start Ollama and try again.")
                else:
                    st.error(status_msg)
                return

            # Step 2: Processing with real local AI
            with st.status("Processing voice note with local AI...", expanded=True) as status_box:
                try:
                    # Transcription
                    status_box.update(
                        label="Transcribing audio with local Whisper model...",
                        state="running",
                    )
                    transcript = transcribe_audio(selected_audio, model_size=whisper_model)

                    if not transcript or not transcript.strip():
                        status_box.update(label="Transcription failed", state="error")
                        st.error("No speech could be detected in the provided audio.")
                        return

                    # Organization via local LLM
                    status_box.update(
                        label=f"Structuring tasks, events, and summary with Ollama ({ollama_model})...",
                        state="running",
                    )
                    structured_data = organize_transcript(transcript, model_name=ollama_model)

                    # Persistence to SQLite
                    status_box.update(
                        label="Saving organized note to local SQLite database...",
                        state="running",
                    )
                    note_id = save_voice_note(
                        transcript=transcript,
                        summary=structured_data.get("summary", ""),
                        tasks=structured_data.get("tasks", []),
                        events=structured_data.get("events", []),
                        people=structured_data.get("people", []),
                        important_points=structured_data.get("important_points", []),
                    )

                    status_box.update(label="Voice note processed successfully!", state="complete")

                    # Load saved record and update session
                    saved_record = get_voice_note_by_id(note_id)
                    st.session_state["current_processed_note"] = saved_record
                    st.rerun()

                except ConnectionError as err:
                    status_box.update(label="Ollama Connection Error", state="error")
                    st.error("Ollama is not running. Start Ollama and try again.")
                    st.caption("Start the Ollama application or run `ollama serve` in a terminal.")

                except LookupError as err:
                    status_box.update(label="Ollama Model Missing", state="error")
                    st.error(str(err))
                    st.code(f"ollama pull {ollama_model}", language="bash")

                except ValueError as err:
                    status_box.update(label="JSON Extraction Error", state="error")
                    st.error(f"Could not parse structured information: {str(err)}")
                    if "transcript" in locals() and transcript:
                        with st.expander("View Raw Transcript"):
                            st.write(transcript)

                except RuntimeError as err:
                    status_box.update(label="Transcription Error", state="error")
                    st.error(f"Whisper Error: {str(err)}")

                except Exception as err:
                    status_box.update(label="Unexpected Processing Error", state="error")
                    st.error(f"An unexpected error occurred: {str(err)}")


if __name__ == "__main__":
    main()
