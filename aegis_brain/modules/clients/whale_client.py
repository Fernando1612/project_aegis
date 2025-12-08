import os
import logging
import aiohttp
import asyncio
from datetime import datetime, timedelta

# Configure logging
logger = logging.getLogger("WhaleWatcher")

class WhaleClient:
    """
    Client for the Whale Alert API (or similar on-chain data provider).
    Normalizes large transaction flows into a 0-1 score.
    
    Score Interpretation:
    0.0 - 0.4: Bearish (Massive Inflows to Exchanges -> Potential Dump)
    0.4 - 0.6: Neutral (Balanced flows or low activity)
    0.6 - 1.0: Bullish (Massive Outflows from Exchanges -> Accumulation)
    """
    def __init__(self, api_key: str, min_value_usd: int = 1000000):
        self.api_key = api_key
        self.base_url = "https://api.whale-alert.io/v1"
        self.min_value_usd = min_value_usd
        self.session = None

    async def _get_session(self):
        if self.session is None:
            self.session = aiohttp.ClientSession()
        return self.session

    async def close(self):
        if self.session:
            await self.session.close()
            self.session = None

    async def fetch_exchange_flows(self, symbol: str = "BTC", hours: int = 24) -> float:
        """
        Fetches transactions for the given symbol over the last N hours.
        Returns a normalized score (0-1).
        """
        if not self.api_key or self.api_key == "your_whale_alert_key_here":
            logger.warning("No valid Whale Alert API key found. Returning Neutral score.")
            return 0.5

        # Note: Free tier of Whale Alert is very limited. 
        # This implementation assumes a hypothetical endpoint or structure 
        # similar to their standard transaction query.
        
        # For MVP/Simulation without a paid key, we might need to mock this 
        # or use a different free source (like scraping Coinglass if allowed).
        
        # Mocking logic for safety if API fails or is unauthorized
        try:
            # Real implementation would be:
            # start_time = int((datetime.now() - timedelta(hours=hours)).timestamp())
            # url = f"{self.base_url}/transactions?api_key={self.api_key}&start={start_time}&currency={symbol.lower()}&min_value={self.min_value_usd}"
            # async with (await self._get_session()).get(url) as response:
            #     data = await response.json()
            #     return self._calculate_score(data)
            
            logger.info(f"Fetching whale data for {symbol} (Simulated)...")
            await asyncio.sleep(0.5) # Simulate network latency
            return 0.5 # Neutral by default
            
        except Exception as e:
            logger.error(f"Error fetching whale data: {e}")
            return 0.5

    def _calculate_score(self, data: dict) -> float:
        """
        Internal logic to process raw transaction list.
        """
        inflow_usd = 0.0
        outflow_usd = 0.0

        transactions = data.get("transactions", [])
        for tx in transactions:
            amount_usd = tx.get("amount_usd", 0)
            from_type = tx.get("from", {}).get("owner_type", "unknown")
            to_type = tx.get("to", {}).get("owner_type", "unknown")

            # Inflow: Unknown/Wallet -> Exchange
            if from_type != "exchange" and to_type == "exchange":
                inflow_usd += amount_usd
            
            # Outflow: Exchange -> Unknown/Wallet
            elif from_type == "exchange" and to_type != "exchange":
                outflow_usd += amount_usd

        net_flow = outflow_usd - inflow_usd
        
        # Normalization Logic
        # If Net Flow is Positive (Outflows > Inflows) -> Bullish -> Score > 0.5
        # If Net Flow is Negative (Inflows > Outflows) -> Bearish -> Score < 0.5
        
        # Sigmoid-ish scaling (simplified)
        # Cap at $100M net flow for max score
        cap = 100_000_000 
        
        normalized = (net_flow / cap) / 2 + 0.5
        return max(0.0, min(1.0, normalized))
