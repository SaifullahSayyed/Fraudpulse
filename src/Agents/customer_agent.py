import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

import random
from src.utils.logger import log_agent_step

_CONFIRMATION_LEVELS = {"medium", "high", "critical"}

def run(risk_level: str, features: dict, transaction_id: str = "unknown") -> dict:
    confirmation_required = risk_level in _CONFIRMATION_LEVELS

    if not confirmation_required:
        result = {
            "confirmation_required": False,
            "customer_response":     "not_required",
            "message":               "No customer confirmation needed for this risk level.",
        }
        log_agent_step("CustomerAgent", transaction_id, result)
        return result

    is_known_device = bool(features.get("is_known_device", True))
    amount          = float(features.get("amount", 0))

    p_confirm = 0.85 if is_known_device else 0.50

    if amount > 5_000:
        p_confirm -= 0.20
    elif amount > 2_000:
        p_confirm -= 0.10

    if risk_level == "critical":
        p_confirm -= 0.10

    p_confirm = max(0.05, min(p_confirm, 0.95))  
    confirmed = random.random() < p_confirm
    response  = "confirmed" if confirmed else "denied"

    message = (
        f"Customer {'confirmed' if confirmed else 'denied'} the transaction "
        f"via simulated OTP / push notification."
    )

    result = {
        "confirmation_required": True,
        "customer_response":     response,
        "message":               message,
    }
    log_agent_step("CustomerAgent", transaction_id, result)
    return result