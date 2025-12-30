import logging
import json
import os
import shutil

from google import genai
from google.genai import types
from datetime import datetime, timedelta

# Import Neuro-Genetic Modules
from .modules.architect import Architect
from .modules.engineer import Engineer
from memory_manager import MemoryManager

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("AEGIS_Evolver")

class EvolutionEngine:
    """
    The "Operation EVO" engine (v3.0).
    Pipeline:
    1. Architect (Gemini): Qualitative Design -> Strategy Template
    2. Engineer (Pymoo): Quantitative Optimization -> Optimized Parameters
    3. Deploy: Compile and Hot-Swap
    """
    def __init__(self, api_key):
        self.api_key = api_key
        self.architect = Architect(api_key)
        self.engineer = Engineer()
        self.memory = MemoryManager()

        # Paths
        self.local_base_path = "/freqtrade/user_data"
        self.strategies_path = os.path.join(self.local_base_path, "strategies")
        self.current_strategy = "AEGIS_Strategy"
        
    def analyze_current_performance(self) -> dict:
        """
        Retrieves recent performance metrics to inform the Architect.
        """
        # Mock for v3.0 MVP - In real life, query DB or Freqtrade API
        return {
            "recent_profit": -2.5, # Mock: We are losing money, triggering innovation
            "market_phase": "BEAR_TREND", 
            "volatility": "HIGH"
        }

    def compile_strategy(self, template_code: str, parameters: dict, class_name: str = "AEGIS_Strategy") -> str:
        """
        Injects optimized parameters into the template and renames the class.
        """
        code = template_code
        
        # 1. Inject Parameters
        for key, value in parameters.items():
            if isinstance(value, str):
                code = code.replace(f"{{key}}", f"'{value}'")
            else:
                code = code.replace(f"{{{key}}}", str(value))
                
        # 2. Rename Class
        # Template usually has AEGIS_Strategy_Template
        code = code.replace("class AEGIS_Strategy_Template", f"class {class_name}")
        
        return code

    def run_evolution_cycle(self):
        """
        Main Neuro-Genetic Loop.
        """
        logger.info("🧬 STARTING NEURO-GENETIC EVOLUTION CYCLE (v3.0) 🧬")
        
        # 1. Context Analysis
        context = self.analyze_current_performance()
        logger.info(f"Market Context: {context}")
        
        # 2. The Architect (Design)
        logger.info("Step 1: Architect designing strategy template...")
        history = self.memory.get_evolution_history(limit=3)
        template, param_defs = self.architect.generate_strategy_template(context, history)
        
        if not template or not param_defs:
            logger.error("Architect failed to produce a valid design. Aborting.")
            return

        logger.info(f"Architect Design Complete. Genes defined: {list(param_defs.keys())}")

        # 3. The Engineer (Optimization)
        logger.info("Step 2: Engineer optimizing parameters with NSGA-II...")
        # Run optimization
        optimized_params = self.engineer.optimize_strategy(template, param_defs, pair="BTC/USDT", generations=10)
        
        if not optimized_params:
            logger.error("Engineer failed to optimize. Aborting.")
            return

        logger.info(f"Engineer Optimization Complete. Optimal Genes: {optimized_params}")

        # 4. Compilation & Deployment
        logger.info("Step 3: Compiling and Deploying Strategy...")
        final_code = self.compile_strategy(template, optimized_params, self.current_strategy)
        
        # Backup old strategy
        current_file = os.path.join(self.strategies_path, f"{self.current_strategy}.py")
        if os.path.exists(current_file):
            shutil.copy(current_file, f"{current_file}.bak")
            
        # Write new strategy
        with open(current_file, 'w') as f:
            f.write(final_code)
            
        # 5. Record History
        self.memory.store_evolution_attempt(
            strategy_name="v3.0_Genetically_Optimized",
            metrics={"context": context}, # simplified
            passed=True,
            reason="Optimized by Engineer"
        )
            
        logger.info("=== EVOLUTION CYCLE COMPLETE: Strategy Updated ===")

