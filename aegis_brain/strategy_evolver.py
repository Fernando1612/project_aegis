import os
import logging
import json
import docker
import sqlite3
import shutil

from google import genai
from google.genai import types

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("AEGIS_Evolver")

from memory_manager import MemoryManager

class EvolutionEngine:
    """
    The "Operation EVO" engine.
    Autonomous cycle: Analyze -> Mutate -> Backtest -> Deploy.
    """
    def __init__(self, api_key):
        self.api_key = api_key
        if api_key:
            self.client = genai.Client(api_key=api_key)
            self.model_name = "gemini-2.5-flash"
        
        # Connect to Docker Daemon (requires /var/run/docker.sock mounted)
        try:
            self.docker_client = docker.from_env()
        except Exception as e:
            logger.error(f"Failed to connect to Docker: {e}")
            self.docker_client = None

        # Paths (Shared Volume)
        # adjusting paths for container execution
        self.local_base_path = "/freqtrade/user_data"
        self.strategies_path = os.path.join(self.local_base_path, "strategies")
        self.db_path = os.path.join(self.local_base_path, "tradesv3.sqlite")
        self.current_strategy = "AEGIS_Strategy"
        self.candidate_strategy = "AEGIS_Strategy_Candidate"
        
        # Initialize Memory
        self.memory = MemoryManager()

    # ... (analyze_current_performance remains)

    def generate_candidate_strategy(self, analysis_summary: str):
        """
        Uses Gemini to write a new strategy file based on analysis and past attempts.
        """
        logger.info("Generating candidate strategy...")
        current_file = os.path.join(self.strategies_path, f"{self.current_strategy}.py")
        
        if not os.path.exists(current_file):
            logger.error(f"Current strategy file not found: {current_file}")
            return False

        with open(current_file, 'r') as f:
            code_content = f.read()

        # Fetch Evolution History for Context
        history = self.memory.get_evolution_history(limit=3)
        history_context = ""
        if history:
            history_context = "\nPAST EVOLUTION ATTEMPTS (LEARN FROM THESE):\n"
            for attempt in history:
                name, metrics, passed, reason = attempt
                history_context += f"- Strategy: {name} | Result: {metrics} | Promoted: {passed} | Barrier: {reason}\n"

        prompt = f"""
        You are a Python Expert specializing in Freqtrade.
        
        CURRENT STRATEGY CODE:
        ```python
        {code_content}
        ```
        
        PERFORMANCE ANALYSIS:
        {analysis_summary}
        
        {history_context}
        
        TASK:
        1. Identify weaknesses in the code based on the analysis.
        2. Modify the code to improve performance.
        3. RENAME the class to `{self.candidate_strategy}`.
        4. KEEP all imports and the `IStrategy` structure.
        
        Output ONLY the valid Python code.
        """
        
        if not hasattr(self, 'client'): 
            logger.error("Gemini Client not initialized.")
            return False

        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt
            )
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
        Workflow: Download Data -> Backtest -> Parse Results -> Cleanup
        """
        logger.info("Running backtest gauntlet...")
        if not self.docker_client:
            return {}

        results = {"profit": 0.0, "drawdown": 0.0, "win_rate": 0.0, "total_trades": 0}

        try:
            container = self.docker_client.containers.get('aegis_pilot')
            
            # 1. Download Data (Binance, 30 days)
            # Using config.json inside container to determine pairs if possible, otherwise hardcoded default for MVP
            logger.info("Step 1: Downloading historical data...")
            dl_cmd = "freqtrade download-data --config /freqtrade/user_data/config.json --days 30 -t 5m"
            dl_log = container.exec_run(dl_cmd)
            if dl_log.exit_code != 0:
                logger.error(f"Data download failed: {dl_log.output.decode('utf-8')}")
                # Fallback to simple download if config fails
                container.exec_run("freqtrade download-data --exchange binance --days 30 -t 5m")

            # 2. Backtest Candidate
            logger.info("Step 2: Running Backtest...")
            # We use --export=json to get machine-readable results
            bt_cmd = f"freqtrade backtesting --strategy {self.candidate_strategy} --timerange=20240101- --days 30 --export=json --export-filename=user_data/backtest_results/backtest-result.json"
            
            exec_log = container.exec_run(bt_cmd)
            output = exec_log.output.decode('utf-8')
            logger.info(f"Backtest Output Snippet: {output[:200]}...")

            # 3. Parse Results (Read JSON from shared volume)
            # The file is inside the container at /freqtrade/user_data/backtest_results/backtest-result.json
            # Use docker exec to cat the file content
            json_cmd = "cat /freqtrade/user_data/backtest_results/backtest-result.json"
            json_log = container.exec_run(json_cmd)
            
            if json_log.exit_code == 0:
                try:
                    bt_data = json.loads(json_log.output.decode('utf-8'))
                    strategy_stats = bt_data['strategy'][self.candidate_strategy]
                    
                    results['profit'] = strategy_stats['total_profit']
                    results['drawdown'] = strategy_stats['max_drawdown_account']
                    # Calculate Win Rate from wins/draws/losses
                    results['total_trades'] = strategy_stats['total_trades']
                    wins = strategy_stats['wins']
                    results['win_rate'] = (wins / results['total_trades']) if results['total_trades'] > 0 else 0.0
                    
                    logger.info(f"Backtest Metrics: {results}")
                except Exception as parse_e:
                    logger.error(f"Failed to parse backtest JSON: {parse_e}")
            else:
                 logger.error("Backtest JSON file not found.")

            # 4. Cleanup Data & Results (To save space as requested)
            logger.info("Step 3: Cleanup...")
            container.exec_run("rm -rf /freqtrade/user_data/data/binance")
            container.exec_run("rm -rf /freqtrade/user_data/backtest_results/*")
            
            return results
            
        except Exception as e:
            logger.error(f"Backtest process failed: {e}")
            return results

    def hot_swap_strategy(self, candidate_metrics: dict, current_metrics: dict):
        """
        Deploys the candidate if it passes strict validation KPIs.
        KPIs: Profit > 5%, Drawdown < 10%, Trades >= 10.
        """
        profit = candidate_metrics.get('profit', 0.0)
        drawdown = candidate_metrics.get('drawdown', 0.0)
        trades = candidate_metrics.get('total_trades', 0)
        
        # Validation Logic
        passed = False
        reason = "Metrics too low"
        
        if profit > 0.05 and drawdown < 0.10 and trades >= 10:
            passed = True
            reason = "KPIs Met: Promoting Strategy"
            logger.info("🚀 SUCCESS: Candidate promoted! (Profit > 5%, DD < 10%, Trades >= 10)")
            # In a real autonomy scenario, we would rename the file here. 
            # For now, we leave it as Candidate for human final approval.
        else:
            if trades < 10:
                reason = f"Insufficient Trades ({trades} < 10)"
            elif profit <= 0.05:
                reason = f"Low Profit ({profit:.2%} <= 5%)"
            elif drawdown >= 0.10:
                reason = f"High Drawdown ({drawdown:.2%} >= 10%)"
                
            logger.info(f"❌ REJECTED: {reason}")
            
            # Cleanup failed candidate
            candidate_file = os.path.join(self.strategies_path, f"{self.candidate_strategy}.py")
            if os.path.exists(candidate_file):
                os.remove(candidate_file)
                logger.info("failed Candidate file removed.")

        # Store Result in Memory
        self.memory.store_evolution_attempt(
            strategy_name=self.candidate_strategy,
            metrics=candidate_metrics,
            passed=passed,
            reason=reason
        )

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
