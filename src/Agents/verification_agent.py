import math
from datetime import datetime
from src.utils.logger import log_agent_step
from src.storage.audit_ledger import ledger
from src.ml.adaptive_weights import adaptive_manager

_RISK_BINS = [
    (25,  "low"),
    (50,  "medium"),
    (75,  "high"),
    (101, "critical"),
]

def _haversine(lat1, lon1, lat2, lon2):
    
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return R * c

def run(fraud_score: float, features: dict, transaction_id: str = "unknown", correlation_id: str = "unknown") -> dict:
    fraud_score = float(fraud_score)
    amount             = float(features.get("amount", 0))
    account_id         = str(features.get("account_id", "anonymous"))
    is_known_device    = bool(features.get("is_known_device", True))
    transaction_hour   = int(features.get("transaction_hour", datetime.utcnow().hour))
    is_foreign         = bool(features.get("is_foreign_transaction", False))
    curr_lat           = float(features.get("latitude", 0))
    curr_lon           = float(features.get("longitude", 0))

    risk_score = fraud_score * 40
    reasons    = []
    fired_rules = []
    
    weights = adaptive_manager.get_weights()

    history = ledger.get_history(account_id, limit=50)
    now = datetime.utcnow()
    
    tx_60s = 0
    total_5m = 0
    tx_count_5m = 0
    
    for tx in history:
        tx_ts = datetime.fromisoformat(tx["timestamp"].replace("Z", ""))
        delta_sec = (now - tx_ts).total_seconds()
        
        if delta_sec <= 60:
            tx_60s += 1
        if delta_sec <= 300:
            total_5m += tx["amount"]
            tx_count_5m += 1

    if tx_60s > 3:
        w = weights.get("rule_velocity", 1.0)
        risk_score += (40 * w)
        reasons.append(f"High velocity: {tx_60s} transactions in 60s (Weight: {w:.2f}x)")
        fired_rules.append("rule_velocity")
    
    if tx_count_5m > 0:
        avg_5m = total_5m / tx_count_5m
        if amount > (3 * avg_5m) and amount > 500:
            w = weights.get("rule_velocity", 1.0)
            risk_score += (25 * w)
            reasons.append(f"Amount (${amount}) is 3x higher than recent 5min average (Weight: {w:.2f}x)")
            if "rule_velocity" not in fired_rules:
                fired_rules.append("rule_velocity")

    last_loc = ledger.get_last_location(account_id)
    if last_loc:
        dist = _haversine(curr_lat, curr_lon, last_loc["lat"], last_loc["lon"])
        last_ts = datetime.fromisoformat(last_loc["ts"].replace("Z", ""))
        time_delta_hr = (now - last_ts).total_seconds() / 3600
        
        if dist > 500 and time_delta_hr < 2:
            w = weights.get("rule_impossible_traveller", 1.0)
            risk_score += (45 * w)
            reasons.append(f"Impossible Traveller: moved {dist:.1f}km in {time_delta_hr:.1f}h (Weight: {w:.2f}x)")
            fired_rules.append("rule_impossible_traveller")
        elif dist > 1000:
            w = weights.get("rule_impossible_traveller", 1.0)
            risk_score += (15 * w)
            reasons.append(f"Significant distance from last known location ({dist:.1f}km) (Weight: {w:.2f}x)")
            if "rule_impossible_traveller" not in fired_rules:
                fired_rules.append("rule_impossible_traveller")

    if amount > 10_000:
        w = weights.get("rule_large_amount", 1.0)
        risk_score += (25 * w)
        reasons.append(f"Very large transaction amount (${amount:,.2f}) (Weight: {w:.2f}x)")
        fired_rules.append("rule_large_amount")
    elif amount > 5_000:
        w = weights.get("rule_large_amount", 1.0)
        risk_score += (15 * w)
        reasons.append(f"Large transaction amount (${amount:,.2f}) (Weight: {w:.2f}x)")
        if "rule_large_amount" not in fired_rules:
            fired_rules.append("rule_large_amount")

    if not is_known_device:
        w = weights.get("rule_unrecognized_device", 1.0)
        risk_score += (20 * w)
        reasons.append(f"Transaction from unrecognised device (Weight: {w:.2f}x)")
        fired_rules.append("rule_unrecognized_device")

    if 0 <= transaction_hour <= 5:
        w = weights.get("rule_unusual_hour", 1.0)
        risk_score += (10 * w)
        reasons.append(f"Transaction at unusual hour ({transaction_hour:02d}:00) (Weight: {w:.2f}x)")
        fired_rules.append("rule_unusual_hour")

    if is_foreign:
        w = weights.get("rule_foreign_tx", 1.0)
        risk_score += (10 * w)
        reasons.append(f"Cross-border / foreign transaction detected (Weight: {w:.2f}x)")
        fired_rules.append("rule_foreign_tx")

    risk_score = round(min(max(risk_score, 0), 100), 2)

    risk_level = "critical"
    for upper, label in _RISK_BINS:
        if risk_score < upper:
            risk_level = label
            break

    if not reasons:
        reasons.append("No significant risk factors identified")

    result = {
        "risk_level":     risk_level,
        "risk_score":     risk_score,
        "reasons":        reasons,
        "fired_rules":    fired_rules,
        "correlation_id": correlation_id
    }
    log_agent_step("VerificationAgent", transaction_id, result)
    return result