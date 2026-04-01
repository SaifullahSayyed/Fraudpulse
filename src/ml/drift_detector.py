import numpy as np
import sqlite3
from src.storage.audit_ledger import ledger

TRAINING_DISTRIBUTION = [0.45, 0.30, 0.20, 0.05]

def calculate_psi(expected: list, actual: list) -> float:
    
    expected = np.array(expected)
    actual = np.array(actual)
    
    actual = np.where(actual == 0, 0.0001, actual)
    expected = np.where(expected == 0, 0.0001, expected)
    
    psi_values = (actual - expected) * np.log(actual / expected)
    return float(np.sum(psi_values))

def compute_model_drift() -> dict:
    
    with sqlite3.connect(ledger.db_path) as conn:
        cursor = conn.execute("SELECT amount FROM fraud_events ORDER BY id DESC LIMIT 1000")
        amounts = [row[0] for row in cursor.fetchall()]
    
    if len(amounts) < 100:
        return {"status": "insufficient_data", "psi": 0.0}
    
    counts = [0] * 4
    for amt in amounts:
        if amt <= 100: counts[0] += 1
        elif amt <= 500: counts[1] += 1
        elif amt <= 2000: counts[2] += 1
        else: counts[3] += 1
    
    actual_dist = [c / len(amounts) for c in counts]
    psi_score = calculate_psi(TRAINING_DISTRIBUTION, actual_dist)
    
    status = "stable"
    if psi_score > 0.25:
        status = "high_drift"
    elif psi_score > 0.1:
        status = "minor_drift"
        
    return {
        "status": status,
        "psi_score": round(psi_score, 4),
        "sample_size": len(amounts),
        "actual_distribution": [round(x, 3) for x in actual_dist]
    }