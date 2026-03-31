import json
import logging
import os
from collections import deque
from datetime import datetime

_BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
LOG_DIR = os.path.join(_BASE_DIR, "logs")
os.makedirs(LOG_DIR, exist_ok=True)

DECISIONS_LOG_PATH = os.path.join(LOG_DIR, "decisions.log")
PIPELINE_LOG_PATH  = os.path.join(LOG_DIR, "pipeline.log")

_decision_buffer: deque = deque(maxlen=500)

_FMT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
_DATE_FMT = "%Y-%m-%dT%H:%M:%S"

_decision_file_handler   = logging.FileHandler(DECISIONS_LOG_PATH, encoding="utf-8")
_decision_stream_handler = logging.StreamHandler()
_decision_file_handler.setFormatter(logging.Formatter(_FMT, datefmt=_DATE_FMT))
_decision_stream_handler.setFormatter(logging.Formatter(_FMT, datefmt=_DATE_FMT))

decision_logger = logging.getLogger("fraudpulse.decisions")
decision_logger.setLevel(logging.INFO)
decision_logger.addHandler(_decision_file_handler)
decision_logger.addHandler(_decision_stream_handler)
decision_logger.propagate = False

_pipeline_file_handler = logging.FileHandler(PIPELINE_LOG_PATH, encoding="utf-8")
_pipeline_file_handler.setFormatter(logging.Formatter(_FMT, datefmt=_DATE_FMT))

pipeline_logger = logging.getLogger("fraudpulse.pipeline")
pipeline_logger.setLevel(logging.DEBUG)
pipeline_logger.addHandler(_pipeline_file_handler)
pipeline_logger.propagate = False

logger = decision_logger

def log_decision(
    transaction_id: str,
    fraud_score: float,
    risk_level: str,
    decision: str,
    reason: str,
) -> dict:
    record = {
        "timestamp":      datetime.utcnow().isoformat() + "Z",
        "transaction_id": transaction_id,
        "fraud_score":    round(float(fraud_score), 4),
        "risk_level":     risk_level,
        "decision":       decision,
        "reason":         reason,
    }
    decision_logger.info(json.dumps(record))
    _decision_buffer.appendleft(record)
    return record

def log_agent_step(agent_name: str, transaction_id: str, data: dict) -> None:
    entry = {
        "agent":          agent_name,
        "transaction_id": transaction_id,
        "timestamp":      datetime.utcnow().isoformat() + "Z",
        **data,
    }
    pipeline_logger.debug(json.dumps(entry))

def get_recent_decisions(limit: int = 50) -> list:
    return list(_decision_buffer)[:limit]

def get_decision_stats() -> dict:
    buf = list(_decision_buffer)
    if not buf:
        return {"total": 0, "avg_fraud_score": 0.0, "breakdown": {}}

    breakdown: dict[str, int] = {}
    for rec in buf:
        key = rec.get("decision", "unknown")
        breakdown[key] = breakdown.get(key, 0) + 1

    avg_score = sum(r.get("fraud_score", 0.0) for r in buf) / len(buf)
    return {
        "total":           len(buf),
        "avg_fraud_score": round(avg_score, 4),
        "breakdown":       breakdown,
    }
