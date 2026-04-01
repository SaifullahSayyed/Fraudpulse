import random

CHAMPION_RULES: dict[str, str] = {
    "low":      "allow",
    "medium":   "verify",
    "high":     "block",
    "critical": "escalate",
}

CHALLENGER_RULES: dict[str, str] = {
    "low":      "allow",
    "medium":   "block",
    "high":     "escalate",
    "critical": "escalate",
}

ACTION_DESCRIPTIONS: dict[str, str] = {
    "allow":    "Transaction is within acceptable risk parameters and has been approved.",
    "verify":   "Transaction requires additional customer verification before proceeding.",
    "block":    "Transaction has been blocked due to elevated fraud risk.",
    "escalate": "Transaction has been escalated to the fraud investigation team.",
}

CHALLENGER_TRAFFIC_PCT: float = 0.10

def decide(risk_level: str) -> dict:
    
    risk_level = str(risk_level).lower().strip()

    if random.random() < CHALLENGER_TRAFFIC_PCT:
        ruleset_name = "CHALLENGER"
        action = CHALLENGER_RULES.get(risk_level, "block")
    else:
        ruleset_name = "CHAMPION"
        action = CHAMPION_RULES.get(risk_level, "block")

    description = ACTION_DESCRIPTIONS.get(action, "Action taken.")

    return {
        "action":       action,
        "description":  description,
        "risk_level":   risk_level,
        "ruleset_name": ruleset_name,
    }