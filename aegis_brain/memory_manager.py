import sqlite3
import json
import logging
from datetime import datetime, timedelta

logger = logging.getLogger("AEGIS_Memory")

class MemoryManager:
    """
    Manages the SQLite database for Project AEGIS.
    Handles storage and retrieval of market snapshots and trade history
    to enable reinforcement learning.
    """
    def __init__(self, db_path="memory.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Initializes the database schema."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Table A: market_snapshots (The Prediction)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS market_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                market_metrics TEXT,
                market_tag TEXT,
                ai_decision TEXT,
                ai_reasoning TEXT,
                outcome_score REAL DEFAULT 0.0,
                is_reconciled BOOLEAN DEFAULT 0
            )
        ''')

        # Table B: trade_history (The Reality)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS trade_history (
                trade_id INTEGER PRIMARY KEY,
                pair TEXT,
                open_timestamp TEXT,
                close_timestamp TEXT,
                profit_pct REAL,
                snapshot_id INTEGER,
                FOREIGN KEY(snapshot_id) REFERENCES market_snapshots(id)
            )
        ''')
        
        # Table C: strategy_evolution (The Labs)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS strategy_evolution (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                strategy_name TEXT,
                metrics_json TEXT,
                passed_validation BOOLEAN,
                rejection_reason TEXT
            )
        ''')
        
        conn.commit()
        conn.close()

    def store_snapshot(self, metrics: dict, tag: str, decision: str, reasoning: str) -> int:
        """Stores a new market snapshot before action is taken."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            '''INSERT INTO market_snapshots 
               (timestamp, market_metrics, market_tag, ai_decision, ai_reasoning) 
               VALUES (?, ?, ?, ?, ?)''',
            (datetime.now().isoformat(), json.dumps(metrics), tag, decision, reasoning)
        )
        snapshot_id = cursor.lastrowid
        conn.commit()
        conn.close()
        logger.info(f"Snapshot stored with ID: {snapshot_id}")
        return snapshot_id

    def get_unreconciled_snapshots(self, hours_back=24):
        """Fetches snapshots that haven't been linked to a trade outcome yet."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        # Look back X hours to avoid processing ancient history
        cutoff = (datetime.now() - timedelta(hours=hours_back)).isoformat()
        cursor.execute(
            "SELECT * FROM market_snapshots WHERE is_reconciled = 0 AND timestamp > ?", 
            (cutoff,)
        )
        rows = cursor.fetchall()
        conn.close()
        return rows

    def update_snapshot_outcome(self, snapshot_id: int, score: float):
        """Updates the outcome score of a snapshot after reconciliation."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE market_snapshots SET outcome_score = ?, is_reconciled = 1 WHERE id = ?",
            (score, snapshot_id)
        )
        conn.commit()
        conn.close()
        logger.info(f"Snapshot {snapshot_id} reconciled with score {score}")

    def store_trade(self, trade_data: dict, snapshot_id: int = None):
        """Stores a closed trade record."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        try:
            cursor.execute(
                '''INSERT OR IGNORE INTO trade_history 
                   (trade_id, pair, open_timestamp, close_timestamp, profit_pct, snapshot_id) 
                   VALUES (?, ?, ?, ?, ?, ?)''',
                (
                    trade_data['trade_id'], 
                    trade_data['pair'], 
                    trade_data['open_date'], # Assuming standard Freqtrade format
                    trade_data['close_date'], 
                    trade_data['profit_ratio'], 
                    snapshot_id
                )
            )
            conn.commit()
        except Exception as e:
            logger.error(f"Error storing trade: {e}")
        finally:
            conn.close()

    def get_similar_snapshots(self, tag: str, limit=3):
        """
        RAG: Retrieves past reconciled snapshots with the same market tag.
        Used to inject context into the LLM prompt.
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            '''SELECT ai_decision, outcome_score, ai_reasoning 
               FROM market_snapshots 
               WHERE market_tag = ? AND is_reconciled = 1 
               ORDER BY id DESC LIMIT ?''',
            (tag, limit)
        )
        rows = cursor.fetchall()
        conn.close()
        return rows

    def store_evolution_attempt(self, strategy_name: str, metrics: dict, passed: bool, reason: str):
        """Stores the result of a strategy evolution cycle."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            '''INSERT INTO strategy_evolution 
               (timestamp, strategy_name, metrics_json, passed_validation, rejection_reason) 
               VALUES (?, ?, ?, ?, ?)''',
            (datetime.now().isoformat(), strategy_name, json.dumps(metrics), passed, reason)
        )
        conn.commit()
        conn.close()
        logger.info(f"Evolution attempt stored: {strategy_name} Passed={passed}")

    def get_evolution_history(self, limit=5):
        """Fetches recent evolution attempts to inform the LLM."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            '''SELECT strategy_name, metrics_json, passed_validation, rejection_reason 
               FROM strategy_evolution 
               ORDER BY id DESC LIMIT ?''',
            (limit,)
        )
        rows = cursor.fetchall()
        conn.close()
        return rows
