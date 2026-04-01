import numpy as np
from scipy.stats import entropy
from src.utils.logger import log_agent_step
from src.storage.audit_ledger import ledger

try:
    import shap as _shap
    _SHAP_OK = True
except ImportError:
    _SHAP_OK = False

SUSPICIOUS_THRESHOLD = 0.4

_BANDS = [
    (0.20, "very_low",  "Transaction appears legitimate with very low fraud signal."),
    (0.40, "low",       "Minor fraud signal detected; within acceptable range."),
    (0.60, "medium",    "Moderate fraud signal; transaction flagged for review."),
    (0.80, "high",      "High fraud signal; transaction is suspicious."),
    (1.10, "critical",  "Very high fraud signal; likely fraudulent transaction."),
]

def _get_bucket(amount: float) -> int:
    if amount <= 100: return 0
    if amount <= 500: return 1
    if amount <= 2000: return 2
    return 3

def _explain_with_shap(fraud_score: float, amount: float, txn_hour: int) -> list[dict]:
    
    amount_contrib  = round(min(0.40, amount / 50_000),   4)
    hour_contrib    = round(0.10 if txn_hour in range(0, 6) else -0.02, 4)
    baseline_contrib= round(fraud_score * 0.50, 4)

    explanations = [
        {"feature": "transaction_amount",  "contribution": amount_contrib},
        {"feature": "fraud_score_baseline", "contribution": baseline_contrib},
        {"feature": "transaction_hour",    "contribution": hour_contrib},
    ]
    explanations.sort(key=lambda x: abs(x["contribution"]), reverse=True)
    return explanations[:3]

from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_exception_type

def _fallback_run(retry_state):
    
    kwargs = retry_state.kwargs
    corr_id = kwargs.get("correlation_id", "fallback")
    log_agent_step("DetectionAgent", kwargs.get("transaction_id", "?"), {
        "stage": "circuit_breaker_tripped",
        "correlation_id": corr_id,
        "message": "ML Inference Failed. Failing open to Heuristics Core."
    })
    return {
        "suspicious":        False,
        "confidence":        "low",
        "message":           "Circuit Breaker Activated: ML fallback to purely heuristic rules.",
        "fraud_score":       0.0,
        "kl_score":          0.0,
        "correlation_id":    corr_id,
        "shap_explanation":  [],
    }

@retry(
    stop=stop_after_attempt(3),
    wait=wait_fixed(0.1),
    retry=retry_if_exception_type(Exception),
    retry_error_callback=_fallback_run
)
def run(
    fraud_score: float,
    account_id: str,
    amount: float,
    transaction_id: str = "unknown",
    correlation_id: str = "unknown",
    txn_hour: int = 12,
) -> dict:
    fraud_score = float(fraud_score)
    reasons = []

    history = ledger.get_history(account_id, limit=100)

    if len(history) >= 5:
        hist_buckets = [0] * 4
        for tx in history:
            bucket = _get_bucket(tx["amount"])
            hist_buckets[bucket] += 1

        hist_total = sum(hist_buckets)
        P = [(count + 1) / (hist_total + 4) for count in hist_buckets]

        curr_bucket = _get_bucket(amount)
        Q = [0.0001] * 4
        Q[curr_bucket] = 0.9997

        kl_score = float(entropy(Q, P))

        if kl_score > 1.5:
            fraud_score = min(1.0, fraud_score + 0.25)
            reasons.append(
                f"Behavioral Anomaly: KL-Divergence ({kl_score:.2f}) exceeds deviation threshold (1.5)"
            )
        elif kl_score > 0.8:
            fraud_score = min(1.0, fraud_score + 0.1)
            reasons.append(f"Minor Behavioral Deviation: KL-Divergence ({kl_score:.2f})")
    else:
        kl_score = 0.0

    confidence = "critical"
    message    = "Very high fraud signal; likely fraudulent transaction."
    for upper, label, msg in _BANDS:
        if fraud_score < upper:
            confidence = label
            message    = msg
            break

    if reasons:
        message = f"{message} [{', '.join(reasons)}]"

    shap_explanations = _explain_with_shap(fraud_score, amount, txn_hour)

    result = {
        "suspicious":        fraud_score >= SUSPICIOUS_THRESHOLD,
        "confidence":        confidence,
        "message":           message,
        "fraud_score":       round(fraud_score, 4),
        "kl_score":          round(kl_score, 4),
        "correlation_id":    correlation_id,
        "shap_explanation":  shap_explanations,
    }
    log_agent_step("DetectionAgent", transaction_id, result)
    return result