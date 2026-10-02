"""Local LLM organizer module using Ollama.

Processes voice note transcripts and extracts structured summaries, tasks,
events, people, and key points in strict JSON format using open-weight local models.
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional, Tuple

import httpx
from dotenv import load_dotenv
import ollama

from utils.helpers import extract_and_validate_json

# Load environment configuration
load_dotenv()


def get_default_ollama_model_name() -> str:
    """Get the configured Ollama model name, defaulting to llama3.2:3b."""
    return os.getenv("OLLAMA_MODEL", "llama3.2:3b").strip() or "llama3.2:3b"


def get_ollama_client(timeout: Optional[float | httpx.Timeout] = None) -> ollama.Client:
    """Instantiate the Ollama client using local host configuration."""
    host = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434").strip()
    if timeout is not None:
        return ollama.Client(host=host, timeout=timeout)
    return ollama.Client(host=host)


def check_ollama_availability(
    model_name: Optional[str] = None,
    timeout_sec: float = 1.5,
) -> Tuple[bool, str, List[str]]:
    """Verify if Ollama service is reachable and whether the requested model is pulled.

    Returns:
        (is_ready, message, available_models_list)
    """
    target_model = model_name or get_default_ollama_model_name()
    client = get_ollama_client(timeout=httpx.Timeout(timeout_sec, connect=timeout_sec))

    try:
        response = client.list()
        # In ollama python client, models can be a list of Model objects or dicts
        available_models: List[str] = []
        raw_models = getattr(response, "models", None) or response.get("models", [])
        for m in raw_models:
            name = getattr(m, "model", None) or getattr(m, "name", None)
            if not name and isinstance(m, dict):
                name = m.get("model") or m.get("name")
            if name:
                available_models.append(str(name))

        # Check if target model or model prefix matches (e.g. 'llama3.2:3b' or 'llama3.2:latest')
        target_base = target_model.split(":")[0]
        has_exact = any(
            m == target_model or m.startswith(f"{target_model}:")
            for m in available_models
        )
        has_base = any(m.startswith(f"{target_base}:") for m in available_models)

        if not (has_exact or has_base):
            return (
                False,
                f"Model '{target_model}' is not available in Ollama. Please run: `ollama pull {target_model}`",
                available_models,
            )

        return (True, f"Ollama is ready with model '{target_model}'.", available_models)

    except (httpx.ConnectError, httpx.ConnectTimeout, ConnectionError, OSError):
        return (False, "Ollama is not running. Start Ollama and try again.", [])
    except Exception as err:
        err_msg = str(err)
        if "connect" in err_msg.lower() or "refused" in err_msg.lower():
            return (False, "Ollama is not running. Start Ollama and try again.", [])
        return (False, f"Ollama error: {err_msg}", [])


ORGANIZER_SYSTEM_PROMPT = """You are an expert AI assistant that organizes voice note transcripts into structured JSON.
You must output ONLY valid JSON matching this exact schema:

{
  "summary": "A concise, clear summary of what the speaker said",
  "tasks": [
    {
      "task": "Description of the actionable task",
      "priority": "High"
    }
  ],
  "events": [
    {
      "event": "Description of the event, meeting, or appointment",
      "date": "Date if mentioned (e.g. Tomorrow, Oct 5), otherwise empty string",
      "time": "Time if mentioned (e.g. 10 AM, 3:30 PM), otherwise empty string"
    }
  ],
  "people": [
    "Names of individuals mentioned in the note"
  ],
  "important_points": [
    "Key points, observations, or facts from the note"
  ]
}

CRITICAL RULES:
1. Do NOT invent, assume, or hallucinate information that was not said in the transcript.
2. If there is no date: "date": ""
3. If there is no time: "time": ""
4. If no people are mentioned: "people": []
5. If no tasks are found: "tasks": []
6. If no events are found: "events": []
7. If no important points are found: "important_points": []
8. Allowed priority values are strictly: "High", "Medium", or "Low".
9. Output ONLY the JSON object. Do not wrap in commentary or markdown explanations.
"""


def organize_transcript(
    transcript: str,
    model_name: Optional[str] = None,
) -> Dict[str, Any]:
    """Send transcript to local Ollama LLM and return structured note information.

    Parameters:
        transcript: The text transcript of the voice note.
        model_name: Optional model identifier (defaults to OLLAMA_MODEL env var or 'llama3.2:3b').

    Returns:
        Structured dictionary containing summary, tasks, events, people, and important_points.

    Raises:
        ConnectionError: If Ollama is not running.
        LookupError: If the specified model is not found in Ollama.
        ValueError: If Ollama output cannot be extracted as valid structured JSON.
        RuntimeError: For other execution failures.
    """
    if not transcript or not transcript.strip():
        raise ValueError("Transcript cannot be empty.")

    target_model = model_name or get_default_ollama_model_name()
    client = get_ollama_client(timeout=httpx.Timeout(180.0, connect=5.0))

    messages = [
        {"role": "system", "content": ORGANIZER_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": f"Organize the following voice note transcript into strict JSON:\n\n{transcript.strip()}",
        },
    ]

    try:
        # Request JSON format explicitly
        response = client.chat(
            model=target_model,
            messages=messages,
            format="json",
            options={
                "temperature": 0.1,  # Low temperature for factual, deterministic extraction
            },
        )
    except (httpx.ConnectError, httpx.ConnectTimeout, ConnectionError, OSError) as err:
        raise ConnectionError(
            "Ollama is not running. Start Ollama and try again."
        ) from err
    except ollama.ResponseError as err:
        if err.status_code == 404 or "not found" in str(err).lower():
            raise LookupError(
                f"Ollama model '{target_model}' was not found. Please run `ollama pull {target_model}` first."
            ) from err
        raise RuntimeError(f"Ollama API error: {err.error}") from err
    except Exception as err:
        err_msg = str(err)
        if "connect" in err_msg.lower() or "refused" in err_msg.lower():
            raise ConnectionError(
                "Ollama is not running. Start Ollama and try again."
            ) from err
        raise RuntimeError(f"Failed to communicate with Ollama: {err_msg}") from err

    # Extract the response content
    try:
        if hasattr(response, "message") and hasattr(response.message, "content"):
            raw_content = response.message.content
        elif isinstance(response, dict) and "message" in response:
            raw_content = response["message"].get("content", "")
        else:
            raw_content = str(response)
    except Exception as err:
        raise RuntimeError(f"Failed to read Ollama response: {str(err)}") from err

    # Parse and validate the JSON
    try:
        structured_data = extract_and_validate_json(raw_content)
        return structured_data
    except Exception as err:
        raise ValueError(
            f"Ollama returned invalid JSON: {str(err)}. Raw output was: {raw_content[:150]}"
        ) from err
