RISK_TO_ACTION: dict[str, str] = {
    "low":      "allow",
    "medium":   "verify",
    "high":     "block",
    "critical": "escalate",
}

ACTION_DESCRIPTIONS: dict[str, str] = {
    "allow":    "Transaction is within acceptable risk parameters and has been approved.",
    "verify":   "Transaction requires additional customer verification before proceeding.",
    "block":    "Transaction has been blocked due to elevated fraud risk.",
    "escalate": "Transaction has been escalated to the fraud investigation team.",
}

def decide(risk_level: str) -> dict:
    risk_level = str(risk_level).lower().strip()
    action      = RISK_TO_ACTION.get(risk_level, "block")   
    description = ACTION_DESCRIPTIONS.get(action, "Action taken.")

    return {
        "action":      action,
        "description": description,
        "risk_level":  risk_level,
    }
