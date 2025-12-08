import os
import logging
import time
import json
import requests
import yaml
import google.generativeai as genai
from datetime import datetime, timedelta
from memory_manager import MemoryManager
from strategy_evolver import EvolutionEngine

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("AEGIS_Brain")

def load_config(config_path="config.yaml"):
    try:
        if not os.path.isabs(config_path):
            base_dir = os.path.dirname(os.path.abspath(__file__))
            config_path = os.path.join(base_dir, config_path)
            
        with open(config_path, 'r') as file:
            return yaml.safe_load(file)
    except Exception as e:
        logger.error(f"Failed to load config from {config_path}: {e}")
        return {}

CONFIG = load_config()


def retry_operation(max_retries=3, delay=2):
    def decorator(func):
        def wrapper(*args, **kwargs):
            for i in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if i == max_retries - 1:
                        logger.error(f"Operation failed after {max_retries} attempts: {e}")
                        raise e
                    logger.warning(f"Operation failed, retrying in {delay}s... ({i+1}/{max_retries})")
                    time.sleep(delay)
        return wrapper
    return decorator

class MCPClient:
    """
    Client to interact with the Kukapay Freqtrade MCP Server.
    """
    def __init__(self, base_url):
        self.base_url = base_url
        logger.info(f"MCP Client initialized for {self.base_url}")

    @retry_operation(max_retries=3, delay=2)
    def list_tools(self):
        try:
            resp = requests.get(f"{self.base_url}/tools")
            return resp.json()
        except Exception as e:
            logger.error(f"Failed to list tools: {e}")
            raise e

    @retry_operation(max_retries=3, delay=2)
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
            raise e

class GeminiClient:
    """
    Wrapper for Google Gemini API with Search Grounding.
    """
    def __init__(self, api_key):
        self.api_key = api_key
        if not api_key:
            logger.warning("GEMINI_API_KEY not set. Running in mock mode.")
        else:
            genai.configure(api_key=api_key)
            # Initialize model with search tools
            self.model = genai.GenerativeModel('gemini-pro', tools='google_search_retrieval')

    @retry_operation(max_retries=3, delay=5)
    def analyze_macro_context(self) -> dict:
        """
        Performs a grounded search for macro-economic and crypto news.
        Returns a sentiment score (-1.0 to 1.0) and a risk flag.
        """
        if not hasattr(self, 'model'):
            return {"score": 0.0, "risk_event": False, "reasoning": "Mock Mode"}

        prompt = """
        Search for the latest news on:
        1. Crypto market regulation (SEC, EU, etc.)
        2. Bitcoin price volatility reasons today
        3. Federal Reserve interest rate news or global macro events

        Analyze the search results and provide a JSON response with:
        - "sentiment_score": A float between -1.0 (Very Bearish) and 1.0 (Very Bullish).
        - "risk_event": Boolean. True ONLY if there is a MAJOR catastrophic event (e.g., Binance hack, War, US ban on crypto).
        - "reasoning": A brief summary of why.
        """
        
        try:
            response = self.model.generate_content(prompt)
            # Simple parsing logic (In prod, use structured output or robust parsing)
            # Assuming LLM returns JSON string block
            text = response.text
            # Strip markdown code blocks if present
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0]
            elif "```" in text:
                text = text.split("```")[1].split("```")[0]
            
            data = json.loads(text)
            logger.info(f"Macro Analysis: {data}")
            return data
        except Exception as e:
            logger.error(f"Macro analysis failed: {e}")
            raise e

    @retry_operation(max_retries=3, delay=5)
    def analyze_market(self, context: dict, memory_context: str = "") -> str:
        """
        Sends market context to Gemini and gets a strategic assessment.
        """
        # Mock response for MVP if model not init
        if not hasattr(self, 'model'):
            return "MARKET_RISK_LOW: Proceed with standard strategy."
            
        prompt = f"""
        You are a crypto trading strategist.
        
        CURRENT MARKET CONTEXT:
        {json.dumps(context)}
        
        MEMORY (PAST LESSONS):
        {memory_context}
        
        Analyze the situation and provide a recommendation.
        """
        try:
            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            logger.error(f"Market analysis failed: {e}")
            raise e

class AegisStrategist:
    def __init__(self):
        self.memory = MemoryManager()
        self.gemini = GeminiClient(os.getenv("GEMINI_API_KEY"))
        self.mcp = MCPClient(os.getenv("MCP_SERVER_URL", "http://mcp_wrapper:8000"))
        self.evolver = EvolutionEngine(os.getenv("GEMINI_API_KEY"))
        self.last_evolution_check = datetime.now()

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
        rsi = context.get('rsi', 50)
        if rsi > 70: return "RSI_HIGH"
        if rsi < 30: return "RSI_LOW"
        return "RSI_NEUTRAL"

    def check_evolution_schedule(self):
        """
        Checks if it's time to run Operation EVO (Sunday 02:00 UTC).
        """
        now = datetime.utcnow()
        # 6 = Sunday. Hour = 2.
        evo_day = CONFIG.get('evolution_day', 6)
        evo_hour = CONFIG.get('evolution_hour', 2)
        
        if now.weekday() == evo_day and now.hour == evo_hour:
            # Ensure we only run once per week (check if we ran in the last hour)
            if now - self.last_evolution_check > timedelta(hours=1):
                logger.info("SCHEDULE TRIGGER: Running Operation EVO...")
                self.evolver.run_evolution_cycle()
                self.last_evolution_check = now

    def run_cycle(self):
        logger.info("Starting strategic cycle...")
        
        # 0. Check Evolution Schedule
        self.check_evolution_schedule()
        
        # 0.5 Reconcile
        try:
            self.reconcile_outcomes()
        except Exception as e:
            logger.error(f"Reconciliation failed: {e}")

        # 1. Fetch Technical Context via MCP
        status = self.mcp.call_tool("fetch_bot_status") or {"status": "unknown"}
        # Mocking technical score for MVP logic (In real app, derive from indicators)
        # 1.0 = Buy, -1.0 = Sell
        tech_score = 0.5 # Neutral-Bullish assumption
        
        # 2. Fetch Macro Context via Gemini Search
        macro_data = self.gemini.analyze_macro_context()
        macro_score = macro_data.get("score", 0.0)
        risk_event = macro_data.get("risk_event", False)
        
        # 3. Circuit Breaker
        if risk_event:
            logger.critical(f"CIRCUIT BREAKER TRIGGERED: {macro_data.get('reasoning')}")
            self.mcp.call_tool("stop_bot")
            return

        # 4. Weighted Decision
        # 60% Technical, 40% Macro
        tech_weight = CONFIG.get('tech_weight', 0.6)
        macro_weight = CONFIG.get('macro_weight', 0.4)
        
        final_score = (tech_score * tech_weight) + (macro_score * macro_weight)
        logger.info(f"Decision Scores - Tech: {tech_score}, Macro: {macro_score}, Final: {final_score}")

        # 5. Execute Action
        action = "HOLD"
        reasoning = f"Weighted Score: {final_score}. Macro: {macro_data.get('reasoning')}"
        
        buy_threshold = CONFIG.get('buy_threshold', 0.6)
        sell_threshold = CONFIG.get('sell_threshold', -0.6)
        
        if final_score > buy_threshold:
            action = "BUY_SIGNAL"
            # self.mcp.call_tool("start_bot") # Or specific buy command
        elif final_score < sell_threshold:
            action = "SELL_SIGNAL"
            # self.mcp.call_tool("stop_bot") # Or specific sell command
            
        logger.info(f"Action: {action} | {reasoning}")
        
        # 6. Store Decision (Snapshot)
        tag = self.get_market_tag(status)
        self.memory.store_snapshot(status, tag, action, reasoning)

if __name__ == "__main__":
    strategist = AegisStrategist()
    
    # Main loop
    while True:
        try:
            logger.info("HEARTBEAT: System is active.")
            strategist.run_cycle()
            # Run every 5 minutes
            time.sleep(CONFIG.get('cycle_interval', 300))
        except Exception as e:
            logger.error(f"Error in main loop: {e}")
            time.sleep(CONFIG.get('error_interval', 60))
