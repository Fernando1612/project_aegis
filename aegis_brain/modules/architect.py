
import logging
import json
import re
from google import genai
from google.genai import types

# Configure logging
logger = logging.getLogger("AEGIS_Architect")

class Architect:
    """
    The Architect (Qualitative Designer).
    Uses Gemini to analyze market context and generate Strategy Templates.
    These templates contain placeholders (GENES) for the Engineer to optimize.
    """
    def __init__(self, api_key):
        self.api_key = api_key
        if api_key:
            self.client = genai.Client(api_key=api_key)
            self.model_name = "gemini-2.5-flash"
        else:
            logger.warning("Architect initialized without API Key. Mock mode.")

    def generate_strategy_template(self, market_context: dict, evolution_history: list = None) -> tuple[str, dict]:
        """
        Generates a Python strategy template with placeholders for optimization.
        
        Args:
            market_context: Dict containing current market analysis (trend, volatility, etc).
            evolution_history: List of past attempts to learn from.
            
        Returns:
            template_code (str): Python code with {placeholders}.
            parameter_definitions (dict): Dictionary defining genes and their ranges.
        """
        logger.info("Architect: Designing new strategy template...")
        
        # 1. Construct Prompt
        context_str = json.dumps(market_context, indent=2)
        history_str = ""
        if evolution_history:
            history_str = "\nPAST EVOLUTION ATTEMPTS (LEARN FROM THESE):\n" + "\n".join([str(h) for h in evolution_history])

        prompt = f"""
        You are the ARCHITECT of the AEGIS Trading System.
        Your goal is to design a high-level trading strategy based on the current market context.
        
        MARKET CONTEXT:
        {context_str}
        
        {history_str}
        
        CRITICAL INSTRUCTION:
        Do NOT write hardcoded numbers for indicators (e.g. RSI < 30).
        Instead, use PLACEHOLDERS in the format `{{variable_name}}`.
        
        We will use a Genetic Algorithm to find the optimal numbers later.
        
        Output a JSON object with two keys:
        1. "template_code": The Python code for the `IStrategy` class. 
           - Class name MUST be `AEGIS_Strategy_Template`.
           - Inherit from `IStrategy`.
           - Inside `populate_indicators`, `populate_entry_trend`, `populate_exit_trend`, use your variables.
           - Example: `dataframe['rsi'] < {{buy_rsi}}`
        
        2. "parameter_definitions": A dictionary defining the variables.
           - Key: variable name (e.g., "buy_rsi")
           - Value: A dictionary with "type" (int/float), "low", "high".
           - Example: `{{"buy_rsi": {{"type": "int", "low": 10, "high": 40}}}}`
           
        Valid Gene Types: "int", "float".
        
        The code must be valid Python (except for the placeholders).
        """
        
        if not hasattr(self, 'client'):
            logger.error("Architect cannot generate: No API Key.")
            return None, None

        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=types.GenerateContentConfig(response_mime_type="application/json")
            )
            
            # Parse Response
            data = json.loads(response.text)
            template_code = data.get("template_code", "")
            parameter_definitions = data.get("parameter_definitions", {})
            
            # Basic Validation
            if "AEGIS_Strategy_Template" not in template_code:
                logger.warning("Architect generated code without correct class name. Forcing fix.")
                template_code = re.sub(r"class \w+\(IStrategy\):", "class AEGIS_Strategy_Template(IStrategy):", template_code)
                
            logger.info(f"Architect produced template with {len(parameter_definitions)} genes.")
            return template_code, parameter_definitions

        except Exception as e:
            logger.error(f"Architect generation failed: {e}")
            return None, None
