from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import os
import logging
import asyncio
from contextlib import asynccontextmanager
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
FREQTRADE_API_URL = os.getenv("FREQTRADE_API_URL")
if not FREQTRADE_API_URL:
    FREQTRADE_API_URL = "http://freqtrade:8080"
FREQTRADE_USERNAME = os.getenv("FREQTRADE_USERNAME", "freqtrader")
FREQTRADE_PASSWORD = os.getenv("FREQTRADE_PASSWORD", "maceda")

# Global session
session: ClientSession | None = None
server_params = StdioServerParameters(
    command="python",
    args=["__main__.py"], # Run the entry point directly
    env={
        "FREQTRADE_API_URL": FREQTRADE_API_URL,
        "FREQTRADE_USERNAME": FREQTRADE_USERNAME,
        "FREQTRADE_PASSWORD": FREQTRADE_PASSWORD,
        **os.environ
    }
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting MCP Bridge...")
    # We can't easily keep a persistent stdio connection in a simple variable 
    # because stdio_client is a context manager.
    # For this MVP, we might need to connect per request or use a long-running task.
    # However, stdio_client is designed to be used with 'async with'.
    # Let's try to keep it open.
    yield
    # Shutdown
    logger.info("Shutting down MCP Bridge...")

app = FastAPI(title="AEGIS Bridge (MCP Server)", version="0.2.0", lifespan=lifespan)

class ToolCall(BaseModel):
    name: str
    arguments: dict = {}

@app.get("/")
async def root():
    return {"status": "online", "service": "AEGIS Bridge", "target": FREQTRADE_API_URL}

@app.get("/tools")
async def list_tools():
    try:
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                tools = await session.list_tools()
                # Convert to simple list of dicts for brain.py
                return [
                    {
                        "name": tool.name,
                        "description": tool.description,
                        "inputSchema": tool.inputSchema
                    } for tool in tools.tools
                ]
    except Exception as e:
        logger.error(f"Error listing tools: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/tools/call")
async def call_tool(call: ToolCall):
    try:
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool(call.name, arguments=call.arguments)
                # Result is a CallToolResult object
                # brain.py expects a JSON response, maybe just the content?
                # Let's return the content list
                return result.content
    except Exception as e:
        logger.error(f"Error calling tool {call.name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
