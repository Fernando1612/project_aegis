import os
import logging
import json
import docker
import sqlite3

from google import genai # New SDK
from datetime import datetime, timedelta

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("AEGIS_Genesis")

class EvolutionManager:
    """
    The 'Project Genesis' Evolution Engine.
    Manages the lifecycle of AEGIS_Strategy, evolving it based on multi-modal inputs.
    """
    def __init__(self, api_key):
        self.api_key = api_key
        if api_key:
            self.client = genai.Client(api_key=api_key)
            self.model_name = 'gemini-2.5-flash'
        
        # Connect to Docker Daemon
        try:
            self.docker_client = docker.from_env()
        except Exception as e:
            logger.error(f"Failed to connect to Docker: {e}")
            self.docker_client = None

        # Paths
        self.strategies_path = "/freqtrade/user_data/strategies"
        self.user_data_path = "/freqtrade/user_data"
        self.db_path = f"{self.user_data_path}/tradesv3.sqlite"
        self.current_strategy_name = "AEGIS_Strategy"
        self.candidate_strategy_name = "AEGIS_Strategy_Candidate"

    def fetch_transaction_history(self) -> str:
        """
        Retrieves transaction history to understand why previous versions won or lost.
        """
        logger.info("Fetching transaction history...")
        if not os.path.exists(self.db_path):
            return "No trading database found."

        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            # Get last 50 trades with details
            cursor.execute("""
                SELECT pair, close_date, close_profit, exit_reason, strategy 
                FROM trades 
                ORDER BY close_date DESC 
                LIMIT 50
            """)
            trades = cursor.fetchall()
            conn.close()
            
            summary = "Recent Transaction History (Last 50 trades):\n"
            for trade in trades:
                summary += f"Pair: {trade[0]}, Profit: {trade[2]}, Reason: {trade[3]}\n"
            return summary
        except Exception as e:
            logger.error(f"DB read failed: {e}")
            return "Error reading transaction history."

    def construct_evolution_prompt(self, current_code: str, history: str) -> str:
        """
        Constructs the System Prompt for the Evolver Agent (Gemini).
        Enforces Input Data Fusion and Anti-Overfitting Protocols.
        """
        # Mocking external inputs for MVP (In a real system, these would come from APIs)
        macro_context = "Market Condition: High Volatility, Interest Rates Stable."
        social_sentiment = "Social Sentiment: Neutral/Fearful."
        
        prompt = f"""
        You are the 'Evolver Agent' for Project AEGIS. Your mission is to evolve the trading strategy `AEGIS_Strategy`.

        ### CONTEXT (Input Data Fusion)
        1. **Macro Context:** {macro_context}
        2. **Social Sentiment:** {social_sentiment}
        3. **Transaction History:** 
           {history}
        
        ### CURRENT STRATEGY CODE
        ```python
        {current_code}
        ```

        ### EVOLUTION DIRECTIVES
        Refactor the code to adapt to the current Context.

        ### ANTI-OVERFITTING PROTOCOLS (Guardrails)
        Warning: You will be penalized for violating these rules.
        1. **Penalty for Complexity (Ockham's Razor):** Do NOT add indicators unless absolutely necessary. Simpler is better. Deduct points for every extra import.
        2. **Reward for Consistency:** Focus on logic that produces consistent wins (high Sharpe/Sortino) rather than lucky home runs.
        3. **Noise Filtering:** Ask yourself: "Is this signal a trend or just noise?" Avoid reacting to single anomalies in the history.
        4. **Robustness:** Ensure logic holds across multiple timeframes.

        ### OUTPUT REQUIREMENTS
        1. **Class Name:** MUST be `{self.candidate_strategy_name}`.
        2. **Inheritance:** MUST inherit from `IStrategy`.
        3. **Imports:** Keep standard Freqtrade imports.
        4. **Format:** Return ONLY the full valid Python code for the file. Run no explanations before or after the code block.
        """
        return prompt

    def evolve_strategy(self):
        """
        Main execution flow: Read -> Prompt -> Write.
        """
        logger.info("Initiating Strategy Evolution...")
        
        # 1. Read
        current_file_path = f"{self.strategies_path}/{self.current_strategy_name}.py"
        # Note: relying on docker volume mount or local path depending on where this runs. 
        # Assuming this runs in the same environment where we just renamed the file.
        # However, the class uses paths starting with /freqtrade which implies container paths.
        # But we are running on the host potentially? 
        # Let's check environment. If running locally on Mac, these paths might need adjustment.
        # For this script generation, I will assume it runs LOCALLY and point to the absolute path 
        # OR I will update the paths to be configurable.
        # Given the previous `strategy_evolver.py` used `/freqtrade/...` it seemingly ran inside docker or assumed that structure.
        # But `BBRSI...` was on the host at `/Users/fernandomaceda...`. 
        # I'll update the paths in `__init__` to be robust or accept arguments.
        # For now, I'll use the user's workspace path for file operations if running locally.
        
        # adjusting paths for local execution based on previous file exploration
        # adjusting paths for container execution
        local_base_path = "/freqtrade/user_data"
        real_strategy_path = os.path.join(local_base_path, "strategies", f"{self.current_strategy_name}.py")
        
        if not os.path.exists(real_strategy_path):
            logger.error(f"Critical: Current strategy file not found at {real_strategy_path}")
            return

        with open(real_strategy_path, "r") as f:
            current_code = f.read()

        # 2. Prepare Data
        history_summary = self.fetch_transaction_history() # valid if db exists locally
        
        if not hasattr(self, 'client'):
             logger.warning("No API Key configured. Skipping generation step.")
             return

        # 3. Prompt
        prompt = self.construct_evolution_prompt(current_code, history_summary)
        
        # 4. Write
        try:
            logger.info("Sending prompt to Gemini...")
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt
            )
            candidate_code = response.text
            
            # Sanitization
            if "```python" in candidate_code:
                candidate_code = candidate_code.split("```python")[1].split("```")[0]
            elif "```" in candidate_code:
                candidate_code = candidate_code.split("```")[1].split("```")[0]
                
            candidate_file_path = os.path.join(local_base_path, "strategies", f"{self.candidate_strategy_name}.py")
            with open(candidate_file_path, "w") as f:
                f.write(candidate_code)
            
            logger.info(f"Evolution complete. Candidate written to: {candidate_file_path}")
            
        except Exception as e:
            logger.error(f"Evolution failed during generation: {e}")

if __name__ == "__main__":
    from dotenv import load_dotenv
    
    # Load environment variables from project root
    # Assuming script is run from project root or aegis_brain
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    load_dotenv(os.path.join(project_root, ".env"))
    
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        logger.error("GEMINI_API_KEY not found in environment variables.")
    else:
        manager = EvolutionManager(api_key)
        manager.evolve_strategy()
        logger.info("Evolution Manager initialized. API Key loaded.")
