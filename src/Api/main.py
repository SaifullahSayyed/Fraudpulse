import sys
import os
import random
import uuid
from datetime import datetime

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from src.orchestration.manager import process_transaction
from src.utils.logger import get_recent_decisions, get_decision_stats

app = FastAPI(
    title="FraudPulse Decision Intelligence API",
    description=(
        "A rule-based fraud detection pipeline exposing Detection, Verification, "
        "Customer, and Escalation agents via a clean REST interface."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],        
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class TransactionRequest(BaseModel):
    fraud_score:           float = Field(..., ge=0.0, le=1.0,
                                         description="ML model output probability of fraud (0–1)")
    amount:                float = Field(0.0,  ge=0.0,
                                         description="Transaction amount in USD")
    is_known_device:       bool  = Field(True,
                                         description="Whether the device is previously recognised")
    transaction_hour:      int   = Field(12,   ge=0, le=23,
                                         description="Hour of transaction (0 = midnight, 23 = 11 PM)")
    is_foreign_transaction: bool = Field(False,
                                         description="Cross-border transaction flag")
    velocity:              int   = Field(1,    ge=1,
                                         description="Number of transactions made by this account in the last hour")
    transaction_id:        str | None = Field(None,
                                         description="Optional transaction ID; auto-generated if omitted")

    model_config = {"json_schema_extra": {
        "example": {
            "fraud_score": 0.72,
            "amount": 4850.00,
            "is_known_device": False,
            "transaction_hour": 2,
            "is_foreign_transaction": True,
            "velocity": 6,
        }
    }}

class BatchSimulateRequest(BaseModel):
    count: int = Field(10, ge=1, le=200,
                       description="Number of random transactions to simulate (max 200)")

@app.get("/health", tags=["System"])
def health_check():
    return {
        "status":    "ok",
        "service":   "FraudPulse API",
        "version":   "1.0.0",
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }

@app.post("/api/v1/analyze", tags=["Analysis"])
def analyze_transaction(req: TransactionRequest):
    features = {
        "amount":                req.amount,
        "is_known_device":       req.is_known_device,
        "transaction_hour":      req.transaction_hour,
        "is_foreign_transaction": req.is_foreign_transaction,
        "velocity":              req.velocity,
    }

    try:
        result = process_transaction(
            fraud_score=req.fraud_score,
            features=features,
            transaction_id=req.transaction_id or str(uuid.uuid4())[:8],
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Pipeline error: {exc}") from exc

    return result

@app.get("/api/v1/decisions", tags=["History"])
def get_decisions(limit: int = Query(50, ge=1, le=500,
                                     description="Number of recent decisions to return")):
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
    for _ in range(req.count):
        fs = random.random()
        features = {
            "amount":                round(random.uniform(1.0, 20_000.0), 2),
            "is_known_device":       random.choice([True, True, False]),   
            "transaction_hour":      random.randint(0, 23),
            "is_foreign_transaction": random.choice([True, False, False]), 
            "velocity":              random.randint(1, 12),
        }
        result = process_transaction(fs, features)
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
