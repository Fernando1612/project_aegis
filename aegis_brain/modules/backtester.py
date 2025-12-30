
import os
import json
import logging
import pandas as pd
import pandas_ta as ta
import numpy as np

# Configure logging
logger = logging.getLogger("AEGIS_Backtester")

class VectorizedBacktester:
    """
    Lightweight, fast backtester using Pandas vectorization.
    Designed to run thousands of simulations per minute on low-end hardware.
    """
    def __init__(self, data_dir="/freqtrade/user_data/data/binance"):
        self.data_dir = data_dir
        self.data_cache = {} # Cache loaded pairs to save I/O

    def load_data(self, pair: str, timeframe: str = "5m", days: int = 30) -> pd.DataFrame:
        """
        Loads OHLCV data from Freqtrade Feather files.
        """
        if pair in self.data_cache:
            return self.data_cache[pair].copy()

        # Handle pair format: "BTC/USDT" -> "BTC_USDT"
        # Freqtrade futures filenames: "BTC_USDT_USDT-5m-futures.feather"
        # We need to try different patterns to find the file
        
        pair_clean = pair.replace("/", "_").replace(":", "_")
        
        # Try finding the file
        candidates = [
            f"{pair_clean}-{timeframe}-futures.feather",
            f"{pair_clean}-{timeframe}.feather",
            f"{pair_clean}-{timeframe}.json" # Fallback
        ]
        
        filepath = None
        for c in candidates:
            p = os.path.join(self.data_dir, c)
            if os.path.exists(p):
                filepath = p
                break
                
        if not filepath:
            logger.error(f"Data file not found for {pair}. Searched in {self.data_dir}")
            return pd.DataFrame()

        try:
            if filepath.endswith(".feather"):
                df = pd.read_feather(filepath)
            else:
                with open(filepath, 'r') as f:
                    data = json.load(f)
                df = pd.DataFrame(data, columns=['date', 'open', 'high', 'low', 'close', 'volume'])
                df['date'] = pd.to_datetime(df['date'], unit='ms')
            
            # Ensure 'date' is datetime
            if 'date' in df.columns:
                 df['date'] = pd.to_datetime(df['date'])
            
            # Filter days
            if days > 0 and 'date' in df.columns:
                start_date = df['date'].iloc[-1] - pd.Timedelta(days=days)
                df = df[df['date'] >= start_date]

            self.data_cache[pair] = df
            return df
        except Exception as e:
            logger.error(f"Failed to load data for {pair}: {e}")
            return pd.DataFrame()

    def run_simulation(self, dataframe: pd.DataFrame, strategy_template: str, parameters: dict) -> dict:
        """
        Injects parameters into the template and runs the simulation.
        
        Args:
            dataframe: OHLCV DataFrame
            strategy_template: String code with {placeholders}
            parameters: Dict of parameter values (e.g., {'rsi_buy': 30})
            
        Returns:
            Dict with metrics (profit_ratio, max_drawdown, win_rate, total_trades)
        """
        df = dataframe.copy()
        
        # 1. Populate Indicators (Dynamic Execution)
        # We need a safe way to execute the logic. 
        # For v3.0, we will assume the template provides logic strings we can eval,
        # OR we inject the logic into a wrapper function.
        
        # NOTE: Executing arbitrary code is risky. In a real system, we'd use an AST parser.
        # Here we trust the internal Architect.
        
        try:
            # Prepare gene values
            # Replace placeholders in the code string is tricky if it's a full class.
            # Simplified approach for v3.0: 
            # The Architect returns logic snippets, e.g., "dataframe['rsi'] < {buy_rsi}"
            # But the Architect returns a FULL CLASS.
            
            # PROPER APPROACH: Use 'exec' to define the class locally, then instantiate it.
            # We need to inject the parameters into the class instance or replace them in source.
            
            # Regex replace matches of {var_name} with value
            filled_code = strategy_template
            for key, value in parameters.items():
                if isinstance(value, str):
                    filled_code = filled_code.replace(f"{{key}}", f"'{value}'")
                else:
                    filled_code = filled_code.replace(f"{{{key}}}", str(value))
            
            # Define namespace for execution
            local_scope = {'pd': pd, 'np': np, 'ta': ta, 'DataFrame': pd.DataFrame}
            
            # Execute the class definition
            exec(filled_code, globals(), local_scope)
            
            # Instantiate the strategy (Class name is fixed by Architect)
            StrategyClass = local_scope.get('AEGIS_Strategy_Template')
            if not StrategyClass:
                logger.error("Strategy class not found in template.")
                return self._empty_result()
                
            strategy = StrategyClass()
            
            # 2. Populate Indicators
            # We need to adapt Freqtrade's IStrategy methods to our lightweight runner
            # Strategy expects 'dataframe' and 'metadata'
            df = strategy.populate_indicators(df, {'pair': 'Generic'})
            df = strategy.populate_entry_trend(df, {'pair': 'Generic'})
            df = strategy.populate_exit_trend(df, {'pair': 'Generic'})
            
            # 3. Vectorized Backtest Calculation
            return self._calculate_vectorized_metrics(df)
            
        except Exception as e:
            logger.error(f"Simulation failed: {e}")
            return self._empty_result()

    def _calculate_vectorized_metrics(self, df: pd.DataFrame) -> dict:
        """
        Calculates profit, drawdown etc from Signals.
        """
        if 'enter_long' not in df.columns or 'exit_long' not in df.columns:
             return self._empty_result()

        # Identify entries and exits
        df['trade_entry'] = (df['enter_long'] == 1) & (df['enter_long'].shift(1) != 1)
        df['trade_exit'] = (df['exit_long'] == 1) & (df['exit_long'].shift(1) != 1)
        
        # Simulation Loop (Vectorized-ish)
        # Pure vectorization is hard for stateful trading (can't buy if already in trade).
        # We iterate for accuracy, but using Numba would be faster. 
        # For now, simple python loop over signals is fast enough for <10k rows.
        
        in_trade = False
        entry_price = 0.0
        trades = []
        equity_curve = [100.0] # start with 100%
        
        # Optimization: Iterate only interesting rows
        signals = df[(df['trade_entry']) | (df['trade_exit'])].copy()
        
        for index, row in signals.iterrows():
            if not in_trade and row['trade_entry']:
                in_trade = True
                entry_price = row['close']
            
            elif in_trade and row['trade_exit']:
                in_trade = False
                exit_price = row['close']
                profit = (exit_price - entry_price) / entry_price
                trades.append(profit)
                
                # Update equity
                last_equity = equity_curve[-1]
                equity_curve.append(last_equity * (1 + profit))
        
        # Metrics
        if not trades:
            return self._empty_result()

        total_profit = equity_curve[-1] - 100.0 # Percentage growth
        
        # Max Drawdown
        equity_series = pd.Series(equity_curve)
        rolling_max = equity_series.cummax()
        drawdown = (equity_series - rolling_max) / rolling_max
        max_drawdown = drawdown.min() # Negative number
        
        win_rate = len([t for t in trades if t > 0]) / len(trades)
        
        return {
            "profit_ratio": total_profit / 100.0,
            "max_drawdown": abs(max_drawdown),
            "win_rate": win_rate,
            "total_trades": len(trades)
        }

    def _empty_result(self):
        return {
            "profit_ratio": -1.0, # Penalty
            "max_drawdown": 1.0,  # Penalty
            "win_rate": 0.0,
            "total_trades": 0
        }
