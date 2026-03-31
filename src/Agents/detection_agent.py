import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from src.utils.logger import log_agent_step

SUSPICIOUS_THRESHOLD = 0.4

_BANDS = [
    (0.20, "very_low",  "Transaction appears legitimate with very low fraud signal."),
    (0.40, "low",       "Minor fraud signal detected; within acceptable range."),
    (0.60, "medium",    "Moderate fraud signal; transaction flagged for review."),
    (0.80, "high",      "High fraud signal; transaction is suspicious."),
    (1.01, "critical",  "Very high fraud signal; likely fraudulent transaction."),
]

def run(fraud_score: float, transaction_id: str = "unknown") -> dict:
    fraud_score = float(fraud_score)
    suspicious  = fraud_score >= SUSPICIOUS_THRESHOLD

    confidence = "critical"
    message    = "Very high fraud signal; likely fraudulent transaction."
    for upper, label, msg in _BANDS:
        if fraud_score < upper:
            confidence = label
            message    = msg
            break

    result = {
        "suspicious":  suspicious,
        "confidence":  confidence,
        "message":     message,
        "fraud_score": round(fraud_score, 4),
    }
    log_agent_step("DetectionAgent", transaction_id, result)
    return result
