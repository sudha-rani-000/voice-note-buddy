FROM python:3.11-slim

# Install system dependencies (curl, ffmpeg)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ffmpeg \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install Ollama CLI and runtime
RUN curl -fsSL https://ollama.com/install.sh | sh

# Create user with UID 1000 for Hugging Face Spaces compatibility
RUN useradd -m -u 1000 user

WORKDIR /home/user/app

# Copy dependencies and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY . .

# Setup permissions for user 1000 and directories
RUN mkdir -p data /home/user/.ollama /home/user/.cache && \
    chown -R user:user /home/user && \
    chmod +x entrypoint.sh

USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH \
    OLLAMA_MODELS=/home/user/.ollama/models

# Expose ports for HF Spaces (7860) and standard Streamlit (8501)
EXPOSE 7860 8501

ENTRYPOINT ["./entrypoint.sh"]
