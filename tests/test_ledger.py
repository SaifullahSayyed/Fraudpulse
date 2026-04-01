import os
import pytest
from src.storage.audit_ledger import AuditLedger

def test_tamper_evident_hashing():
    
    db_path = "test_audit.db"
    if os.path.exists(db_path):
        os.remove(db_path)
        
    ledger = AuditLedger(db_path=db_path)
    
    h1 = ledger.record_event(
        correlation_id="T1", account_id="A1", amount=100.0, 
        decision="allow", agent_chain={}
    )
    
    h2 = ledger.record_event(
        correlation_id="T2", account_id="A2", amount=500.0,
        decision="block", agent_chain={}
    )
    
    assert h1 != h2
    assert len(h1) == 64
    import hashlib
    expected_payload = f"{h1}T2block"
    expected_h2 = hashlib.sha256(expected_payload.encode()).hexdigest()
    
    assert h2 == expected_h2, "Cryptographic hash chain is broken!"
    
    if os.path.exists(db_path):
        os.remove(db_path)