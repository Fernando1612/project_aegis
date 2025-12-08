# pragma pylint: disable=missing-docstring, invalid-name, pointless-string-statement
# flake8: noqa: F401
# isort: skip_file
# --- Do not remove these imports ---
import numpy as np
import pandas as pd
from datetime import datetime, timedelta, timezone
from pandas import DataFrame
from typing import Optional, Union

from freqtrade.strategy import (
    IStrategy,
    Trade,
    Order,
    PairLocks,
    informative,  # @informative decorator
    # Hyperopt Parameters
    BooleanParameter,
    CategoricalParameter,
    DecimalParameter,
    IntParameter,
    RealParameter,
    # timeframe helpers
    timeframe_to_minutes,
    timeframe_to_next_date,
    timeframe_to_prev_date,
    # Strategy helper functions
    merge_informative_pair,
    stoploss_from_absolute,
    stoploss_from_open,
)

# --------------------------------
# Add your lib to import here
import talib.abstract as ta
from technical import qtpylib

class AEGIS_Strategy(IStrategy):
    """
    AEGIS Living Strategy (Project Genesis).

    This strategy is not static. It is autonomously evolved by the AEGIS Evolution Engine.
    It adapts its logic dyamicallly based on multi-modal feedback loops (Macro, Social, History).
    It operates without bias towards any specific indicator, mutating its logic to survive.
    
    CURRENT GENE EXPRESSION:
    - Base Logic: Bollinger Bands + RSI
    - Context: Neutral
    """
    # Strategy interface version - allow new iterations of the strategy interface.
    INTERFACE_VERSION = 3

    # Can this strategy go short?
    can_short: bool = False

    # Minimal ROI designed for the strategy.
    # [EVOLUTION NOTE]: Adjust ROI based on Market Volatility.
    minimal_roi = {
        "60": 0.01,
        "30": 0.03,
        "0": 0.04
    }

    # Optimal stoploss designed for the strategy.
    # [EVOLUTION NOTE]: Tighten stoploss in Bear Markets (-0.05), loosen in Bull (-0.15).
    stoploss = -0.10

    # Trailing stoploss
    trailing_stop = False

    # Optimal timeframe for the strategy.
    timeframe = "5m"

    # Run "populate_indicators()" only for new candle.
    process_only_new_candles = False

    # These values can be overridden in the config.
    use_exit_signal = True
    exit_profit_only = False
    ignore_roi_if_entry_signal = False

    # Number of candles the strategy requires before producing valid signals
    startup_candle_count: int = 30

    # Optional order type mapping.
    order_types = {
        "entry": "limit",
        "exit": "limit",
        "stoploss": "market",
        "stoploss_on_exchange": False,
    }

    # Optional order time in force.
    order_time_in_force = {"entry": "GTC", "exit": "GTC"}

    # --------------------------------------------------------------------------
    # [GENOME SECTION] - Hyperoptable Parameters
    # The Evolution Engine should introduce/remove genes here.
    # --------------------------------------------------------------------------
    buy_rsi = IntParameter(low=10, high=40, default=30, space="buy", optimize=True, load=True)
    sell_rsi = IntParameter(low=60, high=90, default=70, space="sell", optimize=True, load=True)
    
    # Plot configuration
    plot_config = {
        "main_plot": {
            "bb_upperband": {"color": "teal"},
            "bb_lowerband": {"color": "teal"},
            "bb_middleband": {"color": "orange"},
        },
        "subplots": {
            "RSI": {
                "rsi": {"color": "red"},
            },
        },
    }

    def informative_pairs(self):
        """
        Define additional pairs/timeframes to monitor.
        [EVOLUTION NOTE]: Add 'Whale Watcher' pairs here during High Correlation phases.
        """
        return []

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Adds several different TA indicators to the given DataFrame
        [EVOLUTION NOTE]:
        - Penalty for Complexity: Do not add indicators blindly.
        - Use TA-Lib abstract (ta.EMA, ta.RSI, etc.)
        """
        # [GENE] RSI
        dataframe['rsi'] = ta.RSI(dataframe, timeperiod=14)

        # [GENE] Bollinger Bands
        bollinger = qtpylib.bollinger_bands(qtpylib.typical_price(dataframe), window=20, stds=2)
        dataframe['bb_lowerband'] = bollinger['lower']
        dataframe['bb_middleband'] = bollinger['mid']
        dataframe['bb_upperband'] = bollinger['upper']
        
        # [GENE] Volume Check
        # dataframe['volume_mean'] = dataframe['volume'].rolling(24).mean()

        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Based on TA indicators, populates the entry signal for the given dataframe
        [EVOLUTION NOTE]: Define Entry Logic based on current Market Context (Bull/Bear/Crab).
        """
        dataframe.loc[
            (
                # Signal: RSI Oversold
                (dataframe['rsi'] < self.buy_rsi.value) &
                # Signal: Price below Lower Bollinger Band
                (dataframe['close'] < dataframe['bb_lowerband']) &
                # Guardrail: Volume exists
                (dataframe['volume'] > 0)
            ),
            'enter_long'] = 1

        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Based on TA indicators, populates the exit signal for the given dataframe
        [EVOLUTION NOTE]: Define Exit Logic (Profit Taking).
        """
        dataframe.loc[
            (
                # Signal: RSI Overbought
                (dataframe['rsi'] < self.sell_rsi.value) &
                # Signal: Price above Upper Bollinger Band
                (dataframe['close'] > dataframe['bb_upperband']) &
                # Guardrail: Volume exists
                (dataframe['volume'] > 0) 
            ),
            'exit_long'] = 1

        return dataframe

    def confirm_trade_entry(self, pair: str, order_type: str, amount: float, rate: float,
                            time_in_force: str, current_time: datetime, entry_tag: Optional[str],
                            side: str, **kwargs) -> bool:
        """
        Called right before entering a trade.
        [EVOLUTION NOTE]: Use this for "Mental Checks" (News Filters, High Risk Avoidance).
        """
        return True

    def confirm_trade_exit(self, pair: str, trade: Trade, order_type: str, amount: float,
                           rate: float, time_in_force: str, sell_reason: str,
                           current_time: datetime, **kwargs) -> bool:
        """
        Called right before exiting a trade.
        """
        return True
