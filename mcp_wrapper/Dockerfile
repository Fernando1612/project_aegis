FROM python:3.11-slim

WORKDIR /app

# Install git
RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

# Clone the repository
RUN git clone https://github.com/kukapay/freqtrade-mcp.git .

# Install dependencies
RUN pip install --no-cache-dir freqtrade-client "mcp[cli]"

# Expose port (assuming standard MCP or FastAPI port, adjusting if necessary based on repo inspection)
# The docs mention "mcp run __main__.py" which implies it might be a CLI tool interacting via stdio.
# However, for Docker composition, we need it to listen on a port.
# If the MCP server only supports stdio, we might need an SSE wrapper.
# BUT, the user prompt v2 said: "Connects to the Kukapay MCP Server (via stdio or SSE/HTTP depending on the implementation)."
# And "Do NOT write a new server from scratch".
# If the repo is purely stdio, we can't easily reach it from another container without an SSE wrapper.
# Given the constraints and the "mcp[cli]" dependency, it's likely stdio.
# To make it work in Docker, we'll assume we can run it and maybe use a socat bridge or similar if needed,
# OR we assume the user knows what they are doing with "mcp run".
# Wait, the docs say: "The server exposes the following Freqtrade API endpoints as MCP tools".
# Standard MCP over Docker usually requires an SSE transport.
# Let's check if the repo has an SSE option. We can't check.
# We will stick to the instruction: "provide the Dockerfile... needed to deploy the Kukapay repo".
# We will use the command from the docs.
# If it's stdio, the `aegis_brain` would need to run this container or exec into it?
# No, `aegis_brain` is a separate service.
# Let's assume for MVP that we run it and `aegis_brain` might need to use an MCP client that supports remote connections,
# or we wrap it.
# Since I cannot add a complex wrapper without "writing a new server", I will assume the repo has a way to serve.
# If not, I will add a simple python script to wrap it in SSE if I can, but I shouldn't "write a new server".
# Let's just run the main script as requested.

CMD ["python", "__main__.py"]
