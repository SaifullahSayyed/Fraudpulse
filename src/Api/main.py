import sys
import os
import random
import uuid
from datetime import datetime

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator
from typing import List, Dict, Any

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from src.orchestration.manager import process_transaction
from src.utils.logger import get_recent_decisions, get_decision_stats

app = FastAPI(
    title="FraudPulse Decision Intelligence API",
    description=(
        "A hardened rule-based fraud detection pipeline with Pydantic V2 validation, "
        "Idempotency Keys, Circuit Breakers, and Rate Limiting."
    ),
    version="1.2.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

class TransactionRequest(BaseModel):
    account_id:            str   = Field(..., min_length=4, max_length=20,
                                         description="Unique sender account identifier")
    receiver_id:           str   = Field(..., min_length=4, max_length=20,
                                         description="Unique receiver account identifier")
    fraud_score:           float = Field(..., ge=0.0, le=1.0)
    amount:                float = Field(..., ge=0.01)
    latitude:              float = Field(..., ge=-90.0, le=90.0)
    longitude:             float = Field(..., ge=-180.0, le=180.0)
    device_id:             str   = Field(..., min_length=8)
    is_known_device:       bool  = Field(True)
    transaction_hour:      int   = Field(datetime.utcnow().hour, ge=0, le=23)
    is_foreign_transaction: bool = Field(False)
    timestamp:             str   = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    
    @field_validator("amount")
    @classmethod
    def validate_amount(cls, v: float) -> float:
        if v > 10_000_000:
            raise ValueError("Transaction amount exceeds maximum limit of $10M")
        return v

    @field_validator("timestamp")
    @classmethod
    def validate_timestamp(cls, v: str) -> str:
        try:
            ts = datetime.fromisoformat(v.replace("Z", "+00:00"))
            now = datetime.utcnow().replace(tzinfo=None)
            diff = (ts.replace(tzinfo=None) - now).total_seconds()
            if diff > 300:
                raise ValueError("Transaction timestamp is too far in the future")
        except ValueError as e:
            if "too far in the future" in str(e): raise e
            raise ValueError("Invalid ISO8601 timestamp format")
        return v

    model_config = {"json_schema_extra": {
        "example": {
            "account_id": "ACC_SENDER",
            "receiver_id": "ACC_RECEIVER",
            "fraud_score": 0.12,
            "amount": 250.00,
            "latitude": 40.7128,
            "longitude": -74.0060,
            "device_id": "DEV-XYZ-12345",
            "is_known_device": True,
            "transaction_hour": 14,
            "is_foreign_transaction": False,
            "timestamp": "2024-03-01T14:30:15Z"
        }
    }}

class TransactionResponse(BaseModel):
    transaction_id: str
    correlation_id: str
    decision:       str
    risk_level:     str
    reason:         str
    confidence:     float
    execution_ms:   float
    model_monitoring: Dict[str, Any]
    network_analysis: Dict[str, Any]

class BatchSimulateRequest(BaseModel):
    count: int = Field(10, ge=1, le=200,
                       description="Number of random transactions to simulate (max 200)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from fastapi.responses import StreamingResponse
import asyncio
from src.streaming.sse import sse_manager

@app.get("/api/v1/stream", tags=["Analysis"])
async def stream_decisions():
    
    return StreamingResponse(sse_manager.subscribe(), media_type="text/event-stream")

@app.get("/health", tags=["System"])
def health_check():
    return {
        "status":    "ok",
        "service":   "FraudPulse API",
        "version":   "1.1.0",
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }

@app.post("/api/v1/analyze", tags=["Analysis"], response_model=Dict[str, Any])
@limiter.limit("5/second")
def analyze_transaction(request: Request, req: TransactionRequest):
    
    features = req.model_dump()
    
    try:
        result = process_transaction(
            fraud_score=req.fraud_score,
            features=features,
            account_id=req.account_id
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Pipeline error: {exc}") from exc

    return result

@app.post("/api/v1/reverse", tags=["Analysis"])
def reverse_transaction(correlation_id: str, reason: str, operator_id: str = "admin"):
    
    from src.Agents.escalation_agent import reverse_decision
    try:
        success = reverse_decision(correlation_id, reason, operator_id)
        if not success:
            raise HTTPException(status_code=404, detail="Original transaction not found")
        return {"status": "reversed", "correlation_id": correlation_id}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Reversal error: {exc}")

@app.get("/api/v1/decisions", tags=["History"])
def get_decisions(limit: int = Query(50, ge=1, le=500)):
    return {
        "count":     min(limit, 500),
        "decisions": get_recent_decisions(limit),
    }

@app.get("/api/v1/stats", tags=["History"])
def get_stats():
    return get_decision_stats()

@app.post("/api/v1/simulate/batch", tags=["Simulation"])
def simulate_batch(req: BatchSimulateRequest):
    results = []
    for i in range(req.count):
        req_id = f"SIM_{i}_{uuid.uuid4().hex[:6]}"
        fs = random.random()
        payload = {
            "account_id":      f"ACC_{random.randint(1000, 9999)}",
            "fraud_score":     fs,
            "amount":          round(random.uniform(10.0, 15000.0), 2),
            "latitude":        round(random.uniform(-90, 90), 4),
            "longitude":       round(random.uniform(-180, 180), 4),
            "device_id":       f"DEV_{uuid.uuid4().hex[:12]}",
            "is_known_device": random.choice([True, True, False]),
            "transaction_hour": random.randint(0, 23),
            "is_foreign_transaction": random.choice([True, False, False]),
        }
        tr = TransactionRequest(**payload)
        result = process_transaction(tr.fraud_score, tr.model_dump(), tr.account_id)
        results.append(result)

    decisions_summary = {}
    for r in results:
        d = r.get("decision", "unknown")
        decisions_summary[d] = decisions_summary.get(d, 0) + 1

    return {
        "simulated":         req.count,
        "decision_breakdown": decisions_summary,
        "results":           results,
    }