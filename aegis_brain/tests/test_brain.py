import unittest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch
import sys
import os

# Add parent directory to path to import brain
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from brain import AegisStrategist, CONFIG

class TestAegisBrain(unittest.TestCase):
    def setUp(self):
        # Mock environment variables
        with patch.dict(os.environ, {"GEMINI_API_KEY": "test", "MCP_SERVER_URL": "http://test"}):
            self.strategist = AegisStrategist()

    def test_get_market_tag(self):
        # Test RSI Logic
        self.assertEqual(self.strategist.get_market_tag({'rsi': 80}), "RSI_HIGH")
        self.assertEqual(self.strategist.get_market_tag({'rsi': 20}), "RSI_LOW")
        self.assertEqual(self.strategist.get_market_tag({'rsi': 50}), "RSI_NEUTRAL")
        # Test default
        self.assertEqual(self.strategist.get_market_tag({}), "RSI_NEUTRAL")

    @patch('brain.datetime')
    def test_check_evolution_schedule_trigger(self, mock_datetime):
        # Mock time to Sunday 02:00
        mock_now = datetime(2023, 10, 1, 2, 0, 0) # Oct 1 2023 is a Sunday
        mock_datetime.utcnow.return_value = mock_now
        
        # Mock evolver
        self.strategist.evolver = MagicMock()
        # Ensure last check was long ago
        self.strategist.last_evolution_check = mock_now - timedelta(days=1)
        
        # Set config to match
        with patch.dict(CONFIG, {'evolution_day': 6, 'evolution_hour': 2}):
            self.strategist.check_evolution_schedule()
            
        self.strategist.evolver.run_evolution_cycle.assert_called_once()

    @patch('brain.datetime')
    def test_check_evolution_schedule_no_trigger(self, mock_datetime):
        # Mock time to Monday 02:00
        mock_now = datetime(2023, 10, 2, 2, 0, 0) # Oct 2 2023 is a Monday
        mock_datetime.utcnow.return_value = mock_now
        
        self.strategist.evolver = MagicMock()
        
        with patch.dict(CONFIG, {'evolution_day': 6, 'evolution_hour': 2}):
            self.strategist.check_evolution_schedule()
            
        self.strategist.evolver.run_evolution_cycle.assert_not_called()

if __name__ == '__main__':
    unittest.main()
