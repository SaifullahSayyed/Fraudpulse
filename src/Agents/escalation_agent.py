import json
import sqlite3
from src.utils.logger import log_decision, log_agent_step
from src.storage.audit_ledger import ledger

_ACTION_DETAILS: dict[str, str] = {
    "allow":    "Transaction approved and processed normally.",
    "verify":   "Transaction held; awaiting customer verification.",
    "block":    "Transaction blocked due to elevated fraud risk.",
    "escalate": "Transaction escalated to the fraud analyst team for manual review.",
    "reversed":  "Transaction decision has been manually reversed by an operator.",
}

def reverse_decision(correlation_id: str, reason: str, operator_id: str) -> bool:
    
    with sqlite3.connect(ledger.db_path) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.execute(
            "SELECT * FROM fraud_events WHERE correlation_id = ? LIMIT 1", 
            (correlation_id,)
        )
        original = cursor.fetchone()
    
    if not original:
        return False

    ledger.record_event(
        correlation_id=correlation_id,
        account_id=original["account_id"],
        amount=original["amount"],
        decision="reversed",
        agent_chain={
            "original_event_id": original["id"],
            "reversal_reason": reason,
            "operator_id": operator_id
        }
    )

    log_agent_step("EscalationAgent", original["correlation_id"][:8], {
        "event": "manual_reversal",
        "reason": reason,
        "operator": operator_id
    })
    
    return True

def run(
    transaction_id:    str,
    fraud_score:       float,
    risk_level:        str,
    decision:          str,
    reasons:           list,
    customer_response: str = "not_required",
    correlation_id:    str = "unknown"
) -> dict:
    
    if customer_response == "denied" and decision in ("verify", "allow"):
        decision      = "block"
        reasons.insert(0, "Customer denied OTP / push confirmation. Transaction blocked.")

    action_detail = _ACTION_DETAILS.get(decision, "Action taken.")
    reason_text   = " | ".join(reasons) if reasons else "No specific reason recorded."

    payload = {
        "transaction_id":   transaction_id,
        "correlation_id":   correlation_id,
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
    
    log_agent_step("EscalationAgent", transaction_id, {
        "decision": decision, 
        "action_detail": action_detail,
        "correlation_id": correlation_id
    })

    return payload