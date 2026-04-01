import sqlite3
import hashlib
import json
import os
from datetime import datetime

class AuditLedger:
    
    def __init__(self, db_path=None):
        if db_path is None:
            base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
            db_dir = os.path.join(base_dir, "src", "storage")
            os.makedirs(db_dir, exist_ok=True)
            db_path = os.path.join(db_dir, "fraud_audit.db")
        
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS fraud_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    correlation_id TEXT,
                    timestamp TEXT,
                    account_id TEXT,
                    amount REAL,
                    payload_hash TEXT,
                    prev_hash TEXT,
                    decision TEXT,
                    agent_chain_json TEXT
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS system_state (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
            """)
            conn.commit()

    def record_event(self, correlation_id: str, account_id: str, amount: float, decision: str, agent_chain: dict) -> str:
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT payload_hash FROM fraud_events ORDER BY id DESC LIMIT 1")
            row = cursor.fetchone()
            prev_hash = row[0] if row else "0" * 64

            timestamp = datetime.utcnow().isoformat() + "Z"
            
            payload_data = f"{prev_hash}{correlation_id}{decision}"
            payload_hash = hashlib.sha256(payload_data.encode()).hexdigest()

            conn.execute("""
                INSERT INTO fraud_events (
                    correlation_id, timestamp, account_id, amount, 
                    payload_hash, prev_hash, decision, agent_chain_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                correlation_id, timestamp, account_id, amount, 
                payload_hash, prev_hash, decision, json.dumps(agent_chain)
            ))
            conn.commit()
        
        return payload_hash

    def get_history(self, account_id: str, limit: int = 100):
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM fraud_events WHERE account_id = ? ORDER BY timestamp DESC LIMIT ?", 
                (account_id, limit)
            )
            return [dict(row) for row in cursor.fetchall()]

    def get_last_location(self, account_id: str):
        
        history = self.get_history(account_id, limit=5)
        for event in history:
            if event["decision"] in ("allow", "verify"):
                chain = json.loads(event["agent_chain_json"])
                features = chain.get("features", {})
                if "latitude" in features and "longitude" in features:
                    return {
                        "lat": features["latitude"],
                        "lon": features["longitude"],
                        "ts": event["timestamp"]
                    }
        return None

    def set_state(self, key: str, value: dict) -> None:
        
        val_str = json.dumps(value)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("REPLACE INTO system_state (key, value) VALUES (?, ?)", (key, val_str))
            conn.commit()

    def get_state(self, key: str, default: dict = None) -> dict:
        
        if default is None:
            default = {}
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT value FROM system_state WHERE key = ?", (key,))
            row = cursor.fetchone()
            if row:
                return json.loads(row[0])
        return default

ledger = AuditLedger()