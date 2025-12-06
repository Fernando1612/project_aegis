import os
import logging
import time
import json
import requests
from datetime import datetime, timedelta
from memory_manager import MemoryManager

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("AEGIS_Brain")

class MCPClient:
    """
    Client to interact with the Kukapay Freqtrade MCP Server.
    """
    def __init__(self, base_url):
        self.base_url = base_url
        logger.info(f"MCP Client initialized for {self.base_url}")

    def list_tools(self):
        try:
            resp = requests.get(f"{self.base_url}/tools")
            return resp.json()
        except Exception as e:
            logger.error(f"Failed to list tools: {e}")
            return []

    def call_tool(self, tool_name, arguments={}):
        try:
            payload = {
                "name": tool_name,
                "arguments": arguments
            }
            resp = requests.post(f"{self.base_url}/tools/call", json=payload)
            return resp.json()
        except Exception as e:
            logger.error(f"Failed to call tool {tool_name}: {e}")
            return None

class GeminiClient:
    """
    Stub for Google Gemini API interaction.
    """
    def __init__(self, api_key):
        self.api_key = api_key
        if not api_key:
            logger.warning("GEMINI_API_KEY not set. Running in mock mode.")

    def analyze_market(self, context: dict, memory_context: str = "") -> str:
        """
        Sends market context to Gemini and gets a strategic assessment.
        """
        # Mock response for MVP
        logger.info("Querying Gemini with context and memory...")
        logger.info(f"Memory Context Injected: {memory_context}")
        
        # In a real implementation, 'memory_context' would be part of the prompt
        return "MARKET_RISK_LOW: Proceed with standard strategy. No emergency action required."

class AegisStrategist:
    def __init__(self):
        self.memory = MemoryManager()
        self.gemini = GeminiClient(os.getenv("GEMINI_API_KEY"))
        self.mcp = MCPClient(os.getenv("MCP_SERVER_URL", "http://mcp_wrapper:8000"))

    def reconcile_outcomes(self):
        """
        Matches past snapshots with closed trades to reinforce learning.
        """
        logger.info("Running reconciliation...")
        
        # 1. Fetch Closed Trades via MCP
        # Tool name updated to 'fetch_trades' per Kukapay docs
        trades_response = self.mcp.call_tool("fetch_trades", {})
        
        # Assuming response structure based on typical MCP/Freqtrade API
        # If it returns a list directly or a dict with 'trades' key
        trades = []
        if trades_response:
             if isinstance(trades_response, list):
                 trades = trades_response
             elif isinstance(trades_response, dict) and 'trades' in trades_response:
                 trades = trades_response['trades']
             # Handle other potential structures if needed
        
        if not trades:
            logger.warning("No trades fetched for reconciliation.")
            return

        unreconciled_snapshots = self.memory.get_unreconciled_snapshots()

        for snapshot in unreconciled_snapshots:
            # snapshot structure: (id, timestamp, metrics, tag, decision, reasoning, score, reconciled)
            snap_id = snapshot[0]
            snap_time_str = snapshot[1]
            snap_time = datetime.fromisoformat(snap_time_str)

            for trade in trades:
                # Assuming trade has 'open_date' or 'open_timestamp'
                # Freqtrade API usually returns 'open_date'
                open_date_str = trade.get('open_date') or trade.get('open_timestamp')
                if not open_date_str:
                    continue
                    
                trade_open_time = datetime.fromisoformat(open_date_str)
                
                # Match: Snapshot must be within 30 mins BEFORE trade open
                time_diff = trade_open_time - snap_time
                if timedelta(seconds=0) <= time_diff <= timedelta(minutes=30):
                    # Found a match!
                    profit = trade.get('profit_ratio', 0.0)
                    score = 1.0 if profit > 0 else -1.0
                    
                    self.memory.update_snapshot_outcome(snap_id, score)
                    self.memory.store_trade(trade, snap_id)
                    logger.info(f"Reconciled Snapshot {snap_id} with Trade {trade.get('trade_id')} (Profit: {profit})")
                    break

    def get_market_tag(self, context):
        """
        Generates a simple tag for RAG retrieval based on metrics.
        """
        # Context might be complex, extracting RSI if available
        # 'fetch_bot_status' might not return RSI directly. 
        # We might need 'fetch_market_data' but for now we use what we have.
        rsi = context.get('rsi', 50)
        if rsi > 70: return "RSI_HIGH"
        if rsi < 30: return "RSI_LOW"
        return "RSI_NEUTRAL"

    def run_cycle(self):
        logger.info("Starting strategic cycle...")
        
        # 0. Reconcile past outcomes
        try:
            self.reconcile_outcomes()
        except Exception as e:
            logger.error(f"Reconciliation failed: {e}")

        # 1. Fetch Context via MCP
        # Tool name updated to 'fetch_bot_status' per Kukapay docs
        status = self.mcp.call_tool("fetch_bot_status") or {"status": "unknown"}
        logger.info(f"Market Status: {status}")
        
        # 2. RAG: Query Memory
        tag = self.get_market_tag(status)
        past_lessons = self.memory.get_similar_snapshots(tag)
        
        memory_context = ""
        if past_lessons:
            memory_context = "PAST LESSONS:\n"
            for lesson in past_lessons:
                # lesson: (decision, score, reasoning)
                outcome = "PROFIT" if lesson[1] > 0 else "LOSS"
                memory_context += f"- In similar {tag} conditions, you decided {lesson[0]} and result was {outcome}. Reasoning: {lesson[2]}\n"
        
        # 3. Ask LLM
        llm_advice = self.gemini.analyze_market(status, memory_context)
        logger.info(f"Strategist Advice: {llm_advice}")
        
        # 4. Execute Action (if needed)
        action = "HOLD"
        if "EMERGENCY" in llm_advice:
            action = "EMERGENCY_STOP"
            # Tool name updated to 'stop_bot' per Kukapay docs
            self.mcp.call_tool("stop_bot")
        
        # 5. Store Decision (Snapshot)
        self.memory.store_snapshot(status, tag, action, llm_advice)

if __name__ == "__main__":
    strategist = AegisStrategist()
    
    # Main loop
    while True:
        try:
            strategist.run_cycle()
            # Run every 5 minutes
            time.sleep(300)
        except Exception as e:
            logger.error(f"Error in main loop: {e}")
            time.sleep(60)
