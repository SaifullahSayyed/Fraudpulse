import pytest
from src.agents.detection_agent import run

def test_circuit_breaker_fail_open(monkeypatch):
    
    
    def mock_entropy(*args, **kwargs):
        raise RuntimeError("SIMULATED OUT OF MEMORY OOM KILL")
        
    monkeypatch.setattr("src.agents.detection_agent.entropy", mock_entropy)
    
    result = run(
        fraud_score=0.85,
        account_id="ACC_FAIL",
        amount=50000,
        transaction_id="TX_FAIL",
        correlation_id="CORR_FAIL",
        txn_hour=2
    )
    
    assert result["suspicious"] is False, "Fallback didn't fail open!"
    assert result["fraud_score"] == 0.0, "Fallback score should be baseline 0.0"
    assert "Circuit Breaker Activated" in result["message"]