#!/bin/bash
set -e

# Start Ollama daemon in the background
echo "[INFO] Starting Ollama daemon..."
ollama serve &

# Wait for Ollama to become responsive
echo "[INFO] Waiting for Ollama service at 127.0.0.1:11434..."
until curl -s http://127.0.0.1:11434/api/tags > /dev/null; do
    sleep 1
done
echo "[INFO] Ollama service is active!"

# Pull configured model if not present
TARGET_MODEL="${OLLAMA_MODEL:-llama3.2:3b}"
echo "[INFO] Ensuring model '${TARGET_MODEL}' is downloaded..."
ollama pull "$TARGET_MODEL"

# Determine port (7860 for Hugging Face Spaces, 8501 for standard Streamlit)
APP_PORT="${PORT:-7860}"
echo "[INFO] Launching VoiceNote Buddy Streamlit interface on port ${APP_PORT}..."
exec streamlit run app.py --server.port="${APP_PORT}" --server.address=0.0.0.0
