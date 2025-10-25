FROM python:3.9-slim

WORKDIR /app

# Install required system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first to leverage Docker cache
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Create a non-root user and switch to it
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

# Create a directory for the state file with the correct permissions
RUN mkdir -p /home/appuser/.config/youtube-monitor
ENV STATE_FILE=/home/appuser/.config/youtube-monitor/channel_states.json

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Run both scripts concurrently
CMD ["sh", "run.sh"]
