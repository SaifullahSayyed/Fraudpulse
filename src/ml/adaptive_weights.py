import json
from src.storage.audit_ledger import ledger
from src.utils.logger import logger

class AdaptiveWeightManager:
    
    def __init__(self):
        self.state_key = "rule_weights"
        
        self.default_weights = {
            "rule_velocity": 1.0,
            "rule_impossible_traveller": 1.0,
            "rule_large_amount": 1.0,
            "rule_unrecognized_device": 1.0,
            "rule_unusual_hour": 1.0,
            "rule_foreign_tx": 1.0
        }
        
        self.weights = self._load()

    def _load(self) -> dict:
        stored = ledger.get_state(self.state_key, default={})
        weights = dict(self.default_weights)
        weights.update(stored)
        return weights

    def _save(self) -> None:
        ledger.set_state(self.state_key, self.weights)
        logger.info(f"Adaptive weights updated: {self.weights}")

    def get_weights(self) -> dict:
        
        return self.weights

    def apply_feedback(self, fired_rule_ids: list[str], was_correct: bool) -> None:
        
        boost_factor = 1.05
        
        decay_factor = 0.85 

        for rule_id in fired_rule_ids:
            if rule_id not in self.weights:
                continue

            current_weight = self.weights[rule_id]
            
            if was_correct:
                new_weight = min(1.5, current_weight * boost_factor)
            else:
                new_weight = max(0.1, current_weight * decay_factor)
                
            self.weights[rule_id] = round(new_weight, 3)

        self._save()

adaptive_manager = AdaptiveWeightManager()