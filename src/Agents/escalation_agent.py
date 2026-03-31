import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from src.utils.logger import log_decision, log_agent_step

_ACTION_DETAILS: dict[str, str] = {
    "allow":    "Transaction approved and processed normally.",
    "verify":   "Transaction held; awaiting customer verification.",
    "block":    "Transaction blocked due to elevated fraud risk.",
    "escalate": "Transaction escalated to the fraud analyst team for manual review.",
}

def run(
    transaction_id:    str,
    fraud_score:       float,
    risk_level:        str,
    decision:          str,
    reasons:           list,
    customer_response: str = "not_required",
) -> dict:
    
    if customer_response == "denied" and decision in ("verify", "allow"):
        decision      = "block"
        reasons.insert(0, "Customer denied OTP / push confirmation.  Transaction blocked.")

    action_detail = _ACTION_DETAILS.get(decision, "Action taken.")
    reason_text   = " | ".join(reasons) if reasons else "No specific reason recorded."

    payload = {
        "transaction_id":   transaction_id,
        "fraud_score":      round(float(fraud_score), 4),
        "risk_level":       risk_level,
        "decision":         decision,
        "reason":           reason_text,
        "action_detail":    action_detail,
        "customer_response": customer_response,
    }

    log_decision(
        transaction_id=transaction_id,
        fraud_score=fraud_score,
        risk_level=risk_level,
        decision=decision,
        reason=reason_text,
    )
    log_agent_step("EscalationAgent", transaction_id, {"decision": decision, "action_detail": action_detail})

    return payload
