import logging
import google.generativeai as genai
import os

# Configure logging
logger = logging.getLogger("SentimentSniper")

class SocialClient:
    """
    Client for the Sentiment Sniper module.
    Uses Google Gemini (and potentially Search Grounding) to score market hype.
    
    Score Interpretation:
    0.0 - 0.2: Extreme Fear (Panic selling, "It's over")
    0.2 - 0.4: Fear
    0.4 - 0.6: Neutral
    0.6 - 0.8: Greed
    0.8 - 1.0: Extreme Greed (Euphoria, "To the moon")
    """
    def __init__(self, api_key: str):
        self.api_key = api_key
        if api_key and api_key != "your_gemini_key_here":
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel('gemini-1.5-flash')
        else:
            self.model = None
            logger.warning("Gemini API Key missing or invalid. Sentiment Sniper disabled.")

    async def analyze_hype(self, symbol: str = "Bitcoin") -> float:
        """
        Analyzes recent news/social sentiment for the given symbol.
        Returns a normalized Hype Score (0-1).
        """
        if not self.model:
            return 0.5 # Neutral fallback

        try:
            # In a full implementation, we would first fetch news headlines 
            # via a Search API (SerpApi, Google Search, etc.) or use Gemini's 
            # built-in browsing if available.
            # For this MVP, we will ask Gemini to estimate based on its internal knowledge cutoff 
            # OR we can feed it a mock list of "current headlines" if we had a scraper.
            
            # Since we don't have a live search tool connected here yet, 
            # we will simulate the "Analysis" part by asking it to evaluate a hypothetical scenario
            # or (better) just return a neutral score if we can't browse.
            
            # However, to make this functional for the user to test, let's assume 
            # we pass in some text or just ask it for a general sentiment check 
            # (knowing it might be outdated without browsing).
            
            # PROMPT ENGINEERING for Hype Score
            prompt = f"""
            You are a Crypto Sentiment Analyst.
            
            TASK:
            Analyze the general sentiment for {symbol}. 
            Since you cannot browse the live web right now, assume a "Neutral" market structure 
            unless you have specific recent data.
            
            OUTPUT:
            Return ONLY a single float number between 0.0 and 1.0.
            0.0 = Extreme Fear
            1.0 = Extreme Greed
            """
            
            response = self.model.generate_content(prompt)
            score_text = response.text.strip()
            
            try:
                score = float(score_text)
                return max(0.0, min(1.0, score))
            except ValueError:
                logger.error(f"Invalid sentiment score received: {score_text}")
                return 0.5

        except Exception as e:
            logger.error(f"Error analyzing sentiment: {e}")
            return 0.5
