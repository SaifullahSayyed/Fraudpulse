import sys
import os
import uuid

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from src.Agents import detection_agent, verification_agent, customer_agent, escalation_agent
from src.decision_engine import engine
from src.utils.logger import log_agent_step

def process_transaction(
    fraud_score:    float,
    features:       dict,
    transaction_id: str = None,
) -> dict:
    if transaction_id is None:
        transaction_id = str(uuid.uuid4())

    log_agent_step("Orchestrator", transaction_id, {
        "stage": "start",
        "fraud_score": round(float(fraud_score), 4),
        "features": features,
    })

    detection_result = detection_agent.run(fraud_score, transaction_id)

    verification_result = verification_agent.run(fraud_score, features, transaction_id)
    risk_level = verification_result["risk_level"]
    reasons    = list(verification_result["reasons"])           

    reasons.insert(0, detection_result["message"])

    decision_result = engine.decide(risk_level)
    decision        = decision_result["action"]

    customer_result   = customer_agent.run(risk_level, features, transaction_id)
    customer_response = customer_result["customer_response"]

    if customer_result["confirmation_required"]:
        reasons.append(customer_result["message"])

    final_result = escalation_agent.run(
        transaction_id=transaction_id,
        fraud_score=fraud_score,
        risk_level=risk_level,
        decision=decision,
        reasons=reasons,
        customer_response=customer_response,
    )

    final_result["detection"]    = detection_result
    final_result["verification"] = verification_result
    final_result["customer"]     = customer_result
    final_result["engine"]       = decision_result

    log_agent_step("Orchestrator", transaction_id, {
        "stage":    "complete",
        "decision": final_result["decision"],
    })

    return final_result
