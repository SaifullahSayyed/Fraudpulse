import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from datetime import datetime
from src.utils.logger import log_agent_step

_RISK_BINS = [
    (25,  "low"),
    (50,  "medium"),
    (75,  "high"),
    (101, "critical"),
]

def _is_high_risk_hour(hour: int) -> bool:
    return 0 <= hour <= 5

def run(fraud_score: float, features: dict, transaction_id: str = "unknown") -> dict:
    fraud_score = float(fraud_score)
    amount             = float(features.get("amount", 0))
    is_known_device    = bool(features.get("is_known_device", True))
    transaction_hour   = int(features.get("transaction_hour", datetime.utcnow().hour))
    is_foreign         = bool(features.get("is_foreign_transaction", False))
    velocity           = int(features.get("velocity", 1))

    risk_score = fraud_score * 40
    reasons    = []

    if amount > 10_000:
        risk_score += 25
        reasons.append(f"Very large transaction amount (${amount:,.2f})")
    elif amount > 5_000:
        risk_score += 15
        reasons.append(f"Large transaction amount (${amount:,.2f})")
    elif amount > 1_000:
        risk_score += 5
        reasons.append(f"Moderate transaction amount (${amount:,.2f})")

    if not is_known_device:
        risk_score += 20
        reasons.append("Transaction from unrecognised device")

    if _is_high_risk_hour(transaction_hour):
        risk_score += 10
        reasons.append(f"Transaction at unusual hour ({transaction_hour:02d}:00)")

    if is_foreign:
        risk_score += 10
        reasons.append("Cross-border / foreign transaction detected")

    if velocity > 5:
        risk_score += 15
        reasons.append(f"High transaction velocity ({velocity} txns/hr)")
    elif velocity > 3:
        risk_score += 8
        reasons.append(f"Elevated transaction velocity ({velocity} txns/hr)")

    risk_score = round(min(max(risk_score, 0), 100), 2)

    risk_level = "critical"
    for upper, label in _RISK_BINS:
        if risk_score < upper:
            risk_level = label
            break

    if not reasons:
        reasons.append("No significant risk factors identified")

    result = {
        "risk_level":  risk_level,
        "risk_score":  risk_score,
        "reasons":     reasons,
    }
    log_agent_step("VerificationAgent", transaction_id, result)
    return result
