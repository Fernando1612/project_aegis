
import logging
import numpy as np
from pymoo.core.problem import ElementwiseProblem
from pymoo.algorithms.moo.nsga2 import NSGA2
from pymoo.optimize import minimize
from pymoo.operators.crossover.sbx import SBX
from pymoo.operators.mutation.pm import PM
from pymoo.operators.sampling.rnd import FloatRandomSampling, IntegerRandomSampling
from pymoo.termination import get_termination

from .backtester import VectorizedBacktester

# Configure logging
logger = logging.getLogger("AEGIS_Engineer")

class StrategyOptimizationProblem(ElementwiseProblem):
    """
    Pymoo Problem definition for AEGIS Strategy Optimization.
    Objectives:
    1. Maximize Profit (Minimize -Profit)
    2. Minimize Max Drawdown
    """
    def __init__(self, template_code: str, param_defs: dict, dataframe, backtester: VectorizedBacktester):
        self.template_code = template_code
        self.param_defs = param_defs
        self.dataframe = dataframe
        self.backtester = backtester
        self.param_keys = list(param_defs.keys())
        
        # Define Bounds
        xl = [] # Lower bounds
        xu = [] # Upper bounds
        
        for key in self.param_keys:
            xl.append(param_defs[key]['low'])
            xu.append(param_defs[key]['high'])
            
        super().__init__(n_var=len(self.param_keys),
                         n_obj=2, # Profit, DD
                         n_ieq_constr=0,
                         xl=np.array(xl),
                         xu=np.array(xu))

    def _evaluate(self, x, out, *args, **kwargs):
        # 1. Map vector x back to named parameters
        params = {}
        for i, key in enumerate(self.param_keys):
            val = x[i]
            # Enforce types
            if self.param_defs[key].get('type') == 'int':
                params[key] = int(round(val))
            else:
                params[key] = float(val)
                
        # 2. Run Simulation
        metrics = self.backtester.run_simulation(self.dataframe, self.template_code, params)
        
        # 3. Define Objectives (Minimization)
        # Obj 1: Profit (We want Max Profit -> Min -Profit)
        f1 = -1 * metrics['profit_ratio']
        
        # Obj 2: Drawdown (We want Min DD -> Min DD)
        f2 = metrics['max_drawdown']
        
        # Penalize if 0 trades (force exploration)
        if metrics['total_trades'] < 5:
            f1 = 1.0 # High penalty
            f2 = 1.0 # High penalty

        out["F"] = [f1, f2]
        
class Engineer:
    """
    The Engineer (Quantitative Optimizer).
    Runs Genetic Algorithms to refine the Architect's template.
    """
    def __init__(self):
        # Update path to point to futures if detected, or passed via config
        # For now, default to checking known locations in Backtester or passed explicitly
        self.backtester = VectorizedBacktester(data_dir="/freqtrade/user_data/data/binance/futures")

    def optimize_strategy(self, template_code: str, param_defs: dict, pair: str = "BTC/USDT", generations: int = 20, pop_size: int = 40):
        """
        Executes the NSGA-II optimization loop.
        """
        logger.info(f"Engineer: Starting optimization for {pair} ({generations} gens, {pop_size} pop)...")
        
        # 1. Load Data
        df = self.backtester.load_data(pair, timeframe="5m", days=30)
        if df.empty:
            logger.error("Engineer: No data found for optimization.")
            return None

        # 2. Setup Problem
        problem = StrategyOptimizationProblem(template_code, param_defs, df, self.backtester)
        
        # 3. Setup Algorithm (NSGA-II)
        algorithm = NSGA2(
            pop_size=pop_size,
            n_offsprings=10,
            sampling=FloatRandomSampling(),
            crossover=SBX(prob=0.9, eta=15),
            mutation=PM(prob=0.9, eta=20),
            eliminate_duplicates=True
        )
        
        # 4. Run Optimization
        termination = get_termination("n_gen", generations)
        
        res = minimize(problem,
                       algorithm,
                       termination,
                       seed=1,
                       save_history=False,
                       verbose=True) # Verbose for logs
        
        logger.info(f"Engineer: Optimization complete. Time: {res.exec_time}s")
        
        # 5. Select Best Solution (Sharpe-like logic or max profit with reasonable DD)
        if res.F is None:
            logger.error("Engineer: Optimization failed to produce results.")
            return None
            
        # Extract Pareto Front
        # F[:, 0] is -Profit, F[:, 1] is DD
        profits = -res.F[:, 0]
        drawdowns = res.F[:, 1]
        
        best_idx = 0
        best_score = -np.inf
        
        for i in range(len(profits)):
            p = profits[i]
            dd = drawdowns[i]
            
            # Simple Scoring: Profit / (DD + 0.01)
            # Avoid divide by zero
            score = p / (dd + 0.05) 
            
            if score > best_score:
                best_score = score
                best_idx = i
                
        best_params_vector = res.X[best_idx]
        best_metrics = {"profit": profits[best_idx], "drawdown": drawdowns[best_idx]}
        
        # Map back to dict
        final_params = {}
        keys = list(param_defs.keys())
        for i, key in enumerate(keys):
             val = best_params_vector[i]
             if param_defs[key].get('type') == 'int':
                final_params[key] = int(round(val))
             else:
                final_params[key] = float(val)
                
        logger.info(f"Engineer: Winner Selected! Profit: {best_metrics['profit']:.2%}, DD: {best_metrics['drawdown']:.2%}")
        logger.info(f"Genes: {final_params}")
        
        return final_params
