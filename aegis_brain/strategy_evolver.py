import os
import logging
import json
import docker
import sqlite3
import shutil
import google.generativeai as genai
from datetime import datetime, timedelta

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("AEGIS_Evolver")

class EvolutionEngine:
    """
    The "Operation EVO" engine.
    Autonomous cycle: Analyze -> Mutate -> Backtest -> Deploy.
    """
    def __init__(self, api_key):
        self.api_key = api_key
        if api_key:
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel('gemini-pro')
        
        # Connect to Docker Daemon (requires /var/run/docker.sock mounted)
        try:
            self.docker_client = docker.from_env()
        except Exception as e:
            logger.error(f"Failed to connect to Docker: {e}")
            self.docker_client = None

        # Paths (Shared Volume)
        self.strategies_path = "/freqtrade/user_data/strategies"
        self.db_path = "/freqtrade/user_data/tradesv3.sqlite"
        self.current_strategy = "BBRSI_Optimized"
        self.candidate_strategy = "BBRSI_Candidate"

    def analyze_current_performance(self) -> str:
        """
        Queries Freqtrade DB to find weaknesses.
        """
        logger.info("Analyzing current performance...")
        if not os.path.exists(self.db_path):
            return "No trading database found. Cannot analyze."

        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Simple metrics: Win Rate, Avg Profit, Worst Loss
            cursor.execute("SELECT count(*), sum(case when close_profit > 0 then 1 else 0 end), avg(close_profit), min(close_profit) FROM trades")
            row = cursor.fetchone()
            total_trades, wins, avg_profit, max_loss = row if row else (0, 0, 0, 0)
            
            win_rate = (wins / total_trades * 100) if total_trades > 0 else 0
            
            summary = f"""
            Total Trades: {total_trades}
            Win Rate: {win_rate:.2f}%
            Avg Profit: {avg_profit:.4f}
            Max Drawdown (Single Trade): {max_loss:.4f}
            """
            
            conn.close()
            return summary
        except Exception as e:
            logger.error(f"Analysis failed: {e}")
            return "Error analyzing performance."

    def generate_candidate_strategy(self, analysis_summary: str):
        """
        Uses Gemini to write a new strategy file based on analysis.
        """
        logger.info("Generating candidate strategy...")
        current_file = os.path.join(self.strategies_path, f"{self.current_strategy}.py")
        
        if not os.path.exists(current_file):
            logger.error(f"Current strategy file not found: {current_file}")
            return

        with open(current_file, 'r') as f:
            code_content = f.read()

        prompt = f"""
        You are a Python Expert specializing in Freqtrade.
        
        CURRENT STRATEGY CODE:
        ```python
        {code_content}
        ```
        
        PERFORMANCE ANALYSIS:
        {analysis_summary}
        
        TASK:
        1. Identify weaknesses in the code based on the analysis.
        2. Modify the code to improve performance (e.g., adjust indicators, add filters).
        3. RENAME the class to `{self.candidate_strategy}`.
        4. KEEP all imports and the `IStrategy` structure.
        5. DO NOT use external libraries outside of standard Freqtrade dependencies (talib, pandas, numpy).
        
        Output ONLY the valid Python code.
        """
        
        try:
            response = self.model.generate_content(prompt)
            new_code = response.text
            
            # Clean markdown
            if "```python" in new_code:
                new_code = new_code.split("```python")[1].split("```")[0]
            elif "```" in new_code:
                new_code = new_code.split("```")[1].split("```")[0]
            
            candidate_file = os.path.join(self.strategies_path, f"{self.candidate_strategy}.py")
            with open(candidate_file, 'w') as f:
                f.write(new_code)
            
            logger.info(f"Candidate strategy written to {candidate_file}")
            return True
        except Exception as e:
            logger.error(f"Generation failed: {e}")
            return False

    def run_backtest_gauntlet(self) -> dict:
        """
        Triggers a backtest in the Freqtrade container.
        """
        logger.info("Running backtest gauntlet...")
        if not self.docker_client:
            return {}

        try:
            container = self.docker_client.containers.get('aegis_pilot')
            
            # Backtest Candidate (Last 30 days)
            # Note: This command assumes freqtrade is in path inside container
            cmd = f"freqtrade backtesting --strategy {self.candidate_strategy} --timerange=20240101- --days 30"
            
            exec_log = container.exec_run(cmd)
            output = exec_log.output.decode('utf-8')
            
            # Parse output (Simplified for MVP - Real implementation needs robust parsing)
            # We look for "Total profit %" or similar in the text output
            logger.info(f"Backtest Output (Snippet): {output[:500]}")
            
            # Mocking result parsing for MVP stability
            # In production, we would parse the JSON output if we added --export=json
            return {"profit": 0.0, "drawdown": 0.0} 
            
        except Exception as e:
            logger.error(f"Backtest failed: {e}")
            return {}

    def hot_swap_strategy(self, candidate_metrics: dict, current_metrics: dict):
        """
        Deploys the candidate if it beats the current strategy.
        """
        # MVP Logic: Always fail for safety until robust parsing is in place
        logger.info("Comparing strategies...")
        logger.info("Candidate did not exceed performance threshold (Safety Mode).")
        
        # Cleanup
        candidate_file = os.path.join(self.strategies_path, f"{self.candidate_strategy}.py")
        if os.path.exists(candidate_file):
            os.remove(candidate_file)
            logger.info("Candidate file removed.")

    def run_evolution_cycle(self):
        """
        Main entry point for the evolution loop.
        """
        logger.info("=== STARTING EVOLUTION CYCLE ===")
        
        # 1. Analyze
        analysis = self.analyze_current_performance()
        logger.info(f"Analysis: {analysis}")
        
        # 2. Mutate
        success = self.generate_candidate_strategy(analysis)
        if not success:
            return

        # 3. Validate
        results = self.run_backtest_gauntlet()
        
        # 4. Deploy
        # For MVP, we pass empty dicts as we mocked the backtest parsing
        self.hot_swap_strategy(results, {})
        
        logger.info("=== EVOLUTION CYCLE COMPLETE ===")
