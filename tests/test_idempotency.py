import os
import json
import uuid
import hashlib
from src.orchestration.manager import process_transaction
from src.storage.audit_ledger import ledger

def test_idempotent_processing():
    
    acc_id = "ACC_IDEM"
    amount = 543.21
    
    features = {
        "account_id": acc_id,
        "receiver_id": "REC_X",
        "amount": amount,
        "latitude": 40.0,
        "longitude": -74.0,
        "device_id": "DEV_IDEM",
        "is_known_device": True,
        "transaction_hour": 14,
        "is_foreign_transaction": False,
        "transaction_id": str(uuid.uuid4())[:8]
    }
    
    features["unique_nonce"] = str(uuid.uuid4())
    
    res1 = process_transaction(fraud_score=0.1, features=features, account_id=acc_id)
    assert "_is_cached" not in res1
    assert "audit_hash" in res1
    
    res2 = process_transaction(fraud_score=0.1, features=features, account_id=acc_id)
    
    assert res2.get("_is_cached") is True, "Idempotency failed, ML ran twice!"
    assert res1["audit_hash"] == res2["audit_hash"], "Audit ledger mismatch!"
    assert res2["execution_ms"] < res1["execution_ms"], "Cache was suspiciously slow"