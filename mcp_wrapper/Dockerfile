FROM python:3.12-slim

WORKDIR /app

# Install git
RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

# Clone the repository
RUN git clone https://github.com/kukapay/freqtrade-mcp.git .

# Install dependencies
RUN pip install --no-cache-dir freqtrade-client "mcp[cli]" fastapi uvicorn requests

# Copy the bridge script
COPY main.py .

# Run the bridge
CMD ["python", "main.py"]
