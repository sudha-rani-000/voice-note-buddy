"""Speech-to-text module using faster-whisper.

Provides cached model loading and real speech recognition for uploaded and recorded audio files.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Optional

import streamlit as st
from dotenv import load_dotenv
from faster_whisper import WhisperModel

from utils.helpers import cleanup_temp_file, save_temp_audio

# Load environment configuration
load_dotenv()
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")


def get_default_whisper_model_name() -> str:
    """Retrieve Whisper model name from environment or fallback to 'base'."""
    return os.getenv("WHISPER_MODEL", "base").strip() or "base"


@st.cache_resource(show_spinner="Loading local Whisper model...")
def get_whisper_model(model_size: Optional[str] = None) -> WhisperModel:
    """Load and cache faster-whisper model instance across Streamlit reruns.

    Defaults to CPU with int8 quantization for optimal local execution without
    mandatory GPU or CUDA dependencies. Falls back to float32 if int8 is not supported.
    """
    model_name = model_size or get_default_whisper_model_name()
    try:
        return WhisperModel(model_name, device="cpu", compute_type="int8")
    except Exception:
        # Fallback to float32 if int8 unsupported on host instruction set
        return WhisperModel(model_name, device="cpu", compute_type="float32")


def transcribe_audio(audio_source: Any, model_size: Optional[str] = None) -> str:
    """Transcribe an audio file or stream using faster-whisper.

    Parameters:
        audio_source: File path (str/Path), Streamlit UploadedFile, or bytes.
        model_size: Optional whisper model size (e.g. 'base', 'small', 'tiny').

    Returns:
        The transcribed text string.

    Raises:
        RuntimeError: If transcription fails or audio cannot be processed.
    """
    temp_path: Optional[str] = None
    try:
        # Determine audio source path
        if isinstance(audio_source, (str, Path)):
            audio_path = str(audio_source)
            if not Path(audio_path).exists():
                raise FileNotFoundError(f"Audio file not found: {audio_path}")
        else:
            # File buffer or UploadedFile
            original_name = getattr(audio_source, "name", None)
            temp_path = save_temp_audio(audio_source, original_filename=original_name)
            audio_path = temp_path

        model = get_whisper_model(model_size)
        segments, info = model.transcribe(
            audio_path,
            beam_size=5,
            vad_filter=True,  # Filter silence for cleaner results
        )

        transcript_pieces = []
        for segment in segments:
            transcript_pieces.append(segment.text)

        full_transcript = "".join(transcript_pieces).strip()

        if not full_transcript:
            raise RuntimeError(
                "Transcription completed, but no audible speech was detected in the audio."
            )

        return full_transcript

    except Exception as err:
        raise RuntimeError(f"Whisper transcription failed: {str(err)}") from err
    finally:
        if temp_path:
            cleanup_temp_file(temp_path)
