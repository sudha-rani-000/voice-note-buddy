FROM python:3.11-slim

# Install system dependencies (curl, ffmpeg)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ffmpeg \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install Ollama CLI and runtime
RUN curl -fsSL https://ollama.com/install.sh | sh

WORKDIR /app

# Copy dependencies and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY . .

# Ensure data directory exists for SQLite storage
RUN mkdir -p data

# Entrypoint script permissions
RUN chmod +x entrypoint.sh

# Expose Streamlit web interface
EXPOSE 8501

ENTRYPOINT ["./entrypoint.sh"]
