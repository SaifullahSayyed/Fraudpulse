import networkx as nx
import sqlite3
import pandas as pd
from src.storage.audit_ledger import ledger

class FraudNetworkAnalyzer:
    
    def __init__(self):
        self.G = nx.DiGraph()
        self._load_from_ledger()

    def _load_from_ledger(self):
        
        with sqlite3.connect(ledger.db_path) as conn:
            cursor = conn.execute("SELECT account_id, agent_chain_json FROM fraud_events")
            for row in cursor.fetchall():
                import json
                sender = row[0]
                chain = json.loads(row[1])
                receiver = chain.get("features", {}).get("receiver_id")
                if sender and receiver:
                    self.add_transaction(sender, receiver)

    def add_transaction(self, sender: str, receiver: str):
        
        if self.G.has_edge(sender, receiver):
            self.G[sender][receiver]['weight'] += 1
        else:
            self.G.add_edge(sender, receiver, weight=1)

    def analyze_node(self, account_id: str) -> dict:
        
        if not self.G.has_node(account_id):
            return {"status": "not_found"}

        in_degree = self.G.in_degree(account_id)
        out_degree = self.G.out_degree(account_id)
        
        mule_signal = False
        if in_degree > 5 and out_degree < 2:
            mule_signal = True

        clustering = nx.clustering(self.G.to_undirected(), account_id)

        return {
            "in_degree": in_degree,
            "out_degree": out_degree,
            "mule_signal": mule_signal,
            "clustering_coefficient": round(clustering, 3),
            "threat_level": "high" if mule_signal or clustering > 0.8 else "low"
        }

network_analyzer = FraudNetworkAnalyzer()