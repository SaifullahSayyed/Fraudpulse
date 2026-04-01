import time
import uuid

from src.Agents import detection_agent, verification_agent, customer_agent, escalation_agent
from src.decision_engine import engine
from src.utils.logger import log_agent_step
from src.storage.audit_ledger import ledger
from src.streaming.sse import sse_manager
from src.ml.drift_detector import compute_model_drift
from src.graph.network_analyzer import network_analyzer
from src.ml.adaptive_weights import adaptive_manager

def process_transaction(
    fraud_score:    float,
    features:       dict,
    account_id:     str,
) -> dict:
    
    start_time = time.time()
    
    import hashlib
    import json
    payload_hash = hashlib.sha256(json.dumps(features, sort_keys=True).encode()).hexdigest()
    idempotency_key = f"idem_{payload_hash}"
    cached_result = ledger.get_state(idempotency_key)
    if cached_result:
        cached_result["_is_cached"] = True
        cached_result["execution_ms"] = round((time.time() - start_time) * 1000, 2)
        return cached_result

    correlation_id = str(uuid.uuid4())
    transaction_id = features.get("transaction_id", str(uuid.uuid4())[:8])
    receiver_id = features.get("receiver_id", "unknown")

    log_agent_step("Orchestrator", transaction_id, {
        "stage": "start",
        "correlation_id": correlation_id,
        "account_id": account_id,
        "receiver_id": receiver_id,
        "fraud_score": round(float(fraud_score), 4),
    })

    network_analyzer.add_transaction(account_id, receiver_id)
    network_results = network_analyzer.analyze_node(account_id)

    detection_result = detection_agent.run(
        fraud_score=fraud_score,
        account_id=account_id,
        amount=features.get("amount", 0),
        transaction_id=transaction_id,
        correlation_id=correlation_id,
        txn_hour=features.get("transaction_hour", 12),
    )

    verification_result = verification_agent.run(
        fraud_score=fraud_score, 
        features=features, 
        transaction_id=transaction_id,
        correlation_id=correlation_id
    )
    
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
        correlation_id=correlation_id
    )

    execution_ms = round((time.time() - start_time) * 1000, 2)
    final_result["execution_ms"]     = execution_ms
    final_result["correlation_id"]   = correlation_id
    final_result["account_id"]       = account_id
    final_result["ruleset_name"]     = decision_result.get("ruleset_name", "CHAMPION")
    final_result["shap_explanation"] = detection_result.get("shap_explanation", [])
    final_result["fired_rules"]      = verification_result.get("fired_rules", [])
    final_result["adaptive_weights"] = adaptive_manager.get_weights()
    final_result["detection"]        = detection_result

    final_result["model_monitoring"] = compute_model_drift()
    final_result["network_analysis"] = network_results

    audit_hash = ledger.record_event(
        correlation_id=correlation_id,
        account_id=account_id,
        amount=features.get("amount", 0),
        decision=decision,
        agent_chain={
            "detection": detection_result,
            "verification": verification_result,
            "customer": customer_result,
            "engine": decision_result,
            "network": network_results,
            "features": features
        }
    )
    final_result["audit_hash"] = audit_hash

    sse_manager.publish(final_result)

    log_agent_step("Orchestrator", transaction_id, {
        "stage":    "complete",
        "decision": decision,
        "latency":  execution_ms,
        "correlation_id": correlation_id
    })

    ledger.set_state(idempotency_key, final_result)

    return final_result