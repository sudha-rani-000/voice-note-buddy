---
title: VoiceNote Buddy
emoji: 🎙️
colorFrom: indigo
colorTo: purple
sdk: docker
app_port: 7860
pinned: false
---

# VoiceNote Buddy

> **Turn messy voice notes into organized actions.**

VoiceNote Buddy is an open-source, 100% local AI application that transcribes user voice notes and organizes them into actionable tasks, calendar events, key contacts, executive summaries, and important points.

---

## What It Does

VoiceNote Buddy listens to your audio recordings or uploaded voice memos, transcribes the spoken speech with local high-accuracy speech recognition, and structures the unstructured thoughts into clear, organized categories:
- **Concise Summaries**: Understand what the voice note was about in seconds.
- **Actionable Tasks**: Clear tasks prioritized into High, Medium, or Low priority.
- **Important Events**: Time-sensitive events, meetings, or deadlines with extracted dates and times.
- **People Mentioned**: Individuals or colleagues referenced in the recording.
- **Key Points**: Critical takeaways and factual observations.
- **Persistent History**: All voice notes and structured outputs are stored locally in an SQLite database.

---

## Why It Was Built

People frequently record quick voice notes on their phones while driving, walking, or between meetings. These audio notes often become a stream-of-consciousness dump of tasks, reminders, meeting times, and random ideas.

Later, these recordings sit unorganized in audio files because listening back and manually noting down every single task is slow and tedious. 

**VoiceNote Buddy solves this problem**: it converts messy audio into clear, structured, and prioritized actions—without sending private voice data to external cloud services or paying proprietary API fees.

---

## Features

- 🎙️ **Microphone Recording**: Direct, in-browser audio recording.
- 📁 **Multi-format Audio Upload**: Supports `.wav`, `.mp3`, `.m4a`, and `.ogg` files.
- ⚡ **Local Speech Recognition**: High-performance local transcription using `faster-whisper`.
- 🧠 **Local LLM Organization**: Deep structured data extraction powered by `Ollama` and open-weight models (e.g. `llama3.2:3b`).
- 🎯 **Task Extraction & Prioritization**: Automatically tags tasks as High, Medium, or Low urgency.
- 📅 **Event & Appointment Extraction**: Extracts event descriptions, dates, and times.
- 👥 **People Identification**: Identifies people mentioned in the conversation.
- 💡 **Key Points Breakdown**: Highlights notable ideas and details.
- 📜 **Full Transcript Access**: Preserves and displays original transcripts in an expandable section.
- 🗄️ **Persistent SQLite History**: Browse, review, and re-examine past voice notes anytime.
- 🛡️ **Zero Cloud Leaks**: 100% of data, audio, and inference remains entirely on your machine.

---

## Open-Source AI

VoiceNote Buddy is designed from the ground up to demonstrate the power of local, open-source AI:

1. **Speech-to-Text: `faster-whisper`**
   - Implements OpenAI's Whisper model using CTranslate2, delivering 4x speedup and lower memory usage.
   - Runs locally on CPU or GPU without requiring external API tokens or internet access during transcription.
   - Configurable via `WHISPER_MODEL` (`tiny`, `base`, `small`, `medium`, `large-v3`).

2. **Information Extraction & Structuring: `Ollama`**
   - Runs local open-weight large language models such as Meta's `llama3.2:3b`, `mistral`, or `qwen2.5`.
   - Generates strict, validated JSON without sending user transcripts to third-party proprietary APIs.
   - Configurable via `OLLAMA_MODEL` in `.env`.

---

## Architecture & Pipeline

```
  [User Voice Note]
   (Microphone or File Upload: WAV / MP3 / M4A / OGG)
           │
           ▼
  [faster-whisper (Local CTranslate2)]
           │
           ▼
  [Verbatim Transcript]
           │
           ▼
  [Ollama Local LLM (e.g. llama3.2:3b)]
  Prompted for Strict JSON Schema & Zero Hallucination
           │
           ▼
  [JSON Validation & Normalization Engine]
  (Extracts Summary, Tasks, Events, People, Points)
           │
           ▼
  [SQLite Database: data/voice_notes.db]
           │
           ▼
  [Streamlit UI Dashboard & Note History]
```

---

## Installation & Setup

### 1. Prerequisites
- **Python 3.10+** (tested on Python 3.10, 3.11, and 3.12)
- **Ollama** installed on your system ([Download Ollama](https://ollama.com/))

### 2. Clone / Open Project
Navigate to the project directory:
```bash
cd voice-note-buddy
```

### 3. Create a Virtual Environment
```bash
# Windows
python -m venv .venv
.venv\Scripts\activate

# macOS / Linux
python3 -m venv .venv
source .venv/bin/activate
```

### 4. Install Dependencies
```bash
pip install -r requirements.txt
```

### 5. Setup Ollama and Pull Model
Ensure the Ollama service is running:
```bash
ollama serve
```
In a new terminal window, pull the recommended lightweight open-weight model:
```bash
ollama pull llama3.2:3b
```
*(You can also use other models such as `llama3.1:8b`, `mistral:7b`, or `qwen2.5:7b` by setting `OLLAMA_MODEL` in your `.env` file).*

### 6. Environment Configuration
Copy the template configuration:
```bash
# Windows
copy .env.example .env

# macOS / Linux
cp .env.example .env
```
Default `.env` contents:
```env
OLLAMA_MODEL=llama3.2:3b
WHISPER_MODEL=base
```

---

## Running the Application

Launch the Streamlit app:
```bash
streamlit run app.py
```
Or with the virtual environment python directly:
```bash
# Windows
.venv\Scripts\streamlit.exe run app.py

# macOS / Linux
.venv/bin/streamlit run app.py
```
Open your browser at `http://localhost:8501`.

---

## Usage Guide

1. **Select Input Mode**:
   - Use the **Record Voice Note** tab to record directly from your microphone.
   - Or use the **Upload Voice Note** tab to upload an existing `.wav`, `.mp3`, `.m4a`, or `.ogg` recording.
2. **Review Audio**: Listen to the audio preview in the built-in player.
3. **Click "Process Voice Note"**:
   - The app transcribes the audio via `faster-whisper`.
   - The transcript is processed by `Ollama` into structured JSON.
   - The result is saved into the SQLite database.
4. **Inspect Organized Results**:
   - View the executive summary.
   - Review prioritized tasks.
   - Note down events with dates and times.
   - Check identified people and key points.
   - Expand the full transcript anytime.
5. **Access History**: Click any past note in the **Voice Note History** sidebar to reload all its details.

---

## Real Example

### Input Voice Note:
> *"Tomorrow I have DBMS lab at 10 AM. I need to finish my assignment before evening. I also need to call Ravi about the project."*

### AI Structured Output:

#### 📝 AI Summary
> The speaker has a DBMS lab scheduled for tomorrow at 10 AM, must finish their assignment before evening, and plans to call Ravi regarding the project.

#### 🎯 Tasks
- 🔴 **High**: Finish DBMS assignment before evening
- 🟡 **Medium**: Call Ravi about the project

#### 📅 Important Events
- **DBMS lab** (📅 Tomorrow • ⏰ 10 AM)

#### 👥 People Mentioned
- 👤 Ravi

#### 💡 Important Points
- Assignment deadline is before evening.
- Project discussion pending with Ravi.

---

## Deployment (Docker & Cloud)

VoiceNote Buddy is containerized with Docker and Docker Compose, bundling both the Streamlit app and local Ollama daemon into a single self-contained deployment.

### 1. One-Click Cloud Deployment via Docker Compose
On any Linux Cloud Server (AWS EC2, DigitalOcean Droplet, Hetzner, GCP Compute Engine):

```bash
# Clone your repository
git clone https://github.com/<your-username>/voice-note-buddy.git
cd voice-note-buddy

# Start the full stack in background
docker compose up -d
```
The container automatically:
1. Boots the embedded Ollama service.
2. Pulls `llama3.2:3b`.
3. Serves Streamlit at port `8501`.
4. Mounts persistent storage for `data/voice_notes.db` and model weights.

---

## Future Improvements

- 📆 **Calendar Sync**: One-click export of extracted events directly into Google Calendar or `.ics` files.
- 🔔 **System Reminders**: Integration with OS desktop notifications for high-priority tasks.
- 🌐 **Multilingual Support**: Automatic language detection and translation across 50+ languages supported by Whisper.
- 💬 **Messaging Integration**: Ingestion of WhatsApp or Telegram voice notes via local bot webhook.
- 🏷️ **Custom Tags & Folders**: Organization of notes into categories (Work, Personal, Ideas, Study).
- 🗣️ **Speaker Diarization**: Multi-speaker identification using pyannote.audio.

---

## License

VoiceNote Buddy is distributed under the MIT License. See [LICENSE](LICENSE) for details.
#   v o i c e - n o t e - b u d d y  
 