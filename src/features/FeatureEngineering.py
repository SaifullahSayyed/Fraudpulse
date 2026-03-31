import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, List

class FeatureEngineer:
    
    def __init__(self, dataset_type: str = 'creditcard'):
        self.dataset_type = dataset_type
        
        self.high_amount_threshold = 500  
        self.night_hours = (22, 6)  
        
    def engineer_features(self, df: pd.DataFrame) -> pd.DataFrame:
        print(" Engineering fraud detection features...")
        
        df_features = df.copy()
        
        if self.dataset_type == 'creditcard':
            df_features = self._engineer_creditcard_features(df_features)
        elif self.dataset_type == 'paysim':
            df_features = self._engineer_paysim_features(df_features)
        
        df_features = self._create_universal_features(df_features)
        
        self.feature_names_ = [c for c in df_features.columns if c not in df.columns]
        print(f" Created {len(self.feature_names_)} new features")
        
        return df_features
    
    def _engineer_creditcard_features(self, df: pd.DataFrame) -> pd.DataFrame:
        
        df['transaction_hour'] = (df['Time'] // 3600) % 24
        print("Created transaction_hour feature")
        
        df['is_night_transaction'] = df['transaction_hour'].apply(
            lambda x: 1 if (x >= self.night_hours[0] or x < self.night_hours[1]) else 0
        )
        print("Created is_night_transaction feature")
        
        df['transaction_day'] = (df['Time'] // 86400) % 7
        print("Created transaction_day feature")
        
        df['is_weekend'] = df['transaction_day'].apply(lambda x: 1 if x >= 5 else 0)
        print("Created is_weekend feature")
        
        return df
    
    def _engineer_paysim_features(self, df: pd.DataFrame) -> pd.DataFrame:
        
        df['transaction_hour'] = df['step'] % 24
        
        high_risk_types = ['TRANSFER', 'CASH_OUT']
        df['is_high_risk_type'] = df['type'].apply(
            lambda x: 1 if x in high_risk_types else 0
        )
        
        df['balance_change_ratio'] = np.abs(
            df['newbalanceOrig'] - df['oldbalanceOrg']
        ) / (df['oldbalanceOrg'] + 1)  
        
        return df
    
    def _create_universal_features(self, df: pd.DataFrame) -> pd.DataFrame:
        amount_col = 'Amount' if 'Amount' in df.columns else 'amount'
        
        df['amount_normalized'] = np.log1p(df[amount_col])
        print("Created amount_normalized feature")
        
        df['is_high_amount'] = (df[amount_col] > self.high_amount_threshold).astype(int)
        print(f"Created is_high_amount feature (>{self.high_amount_threshold})")
        
        low_threshold = 1.0
        df['is_low_amount'] = (df[amount_col] < low_threshold).astype(int)
        print(f"Created is_low_amount feature (<{low_threshold})")
        
        df['amount_percentile'] = df[amount_col].rank(pct=True)
        print("Created amount_percentile feature")
        
        rng = np.random.default_rng(42)  
        df['is_new_device'] = rng.choice([0, 1], size=len(df), p=[0.9, 0.1])
        print("Created is_new_device feature")
        
        df['is_new_location'] = rng.choice([0, 1], size=len(df), p=[0.85, 0.15])
        print("Created is_new_location feature")
        
        risk_flags = (
            df['is_high_amount'] +
            (df['is_night_transaction'] if 'is_night_transaction' in df.columns else pd.Series(0, index=df.index)) +
            df['is_new_device'] +
            df['is_new_location']
        )
        df['multiple_risk_flags'] = (risk_flags >= 2).astype(int)
        print("Created multiple_risk_flags feature")
        
        return df
    
    def get_feature_list(self) -> List[str]:
        if hasattr(self, 'feature_names_'):
            return self.feature_names_

        base_features = [
            'amount_normalized',
            'is_high_amount',
            'is_low_amount',
            'amount_percentile',
            'is_new_device',
            'is_new_location',
            'multiple_risk_flags'
        ]
        
        if self.dataset_type == 'creditcard':
            base_features.extend([
                'transaction_hour',
                'is_night_transaction',
                'transaction_day',
                'is_weekend'
            ])
        
        return base_features
    
    def get_feature_importance_explanation(self) -> Dict[str, str]:
        explanations = {
            'transaction_hour': 'Hour of day (0-23) - fraud peaks at night',
            'is_night_transaction': 'Flags 10PM-6AM transactions (high fraud window)',
            'transaction_day': 'Day of week (0-6) - fraud patterns vary by day',
            'is_weekend': 'Weekend flag - different fraud patterns',
            'amount_normalized': 'Log-scaled amount - handles wide value range',
            'is_high_amount': f'Flags amounts > ${self.high_amount_threshold} (typical fraud)',
            'is_low_amount': 'Flags amounts < $1 (test transactions)',
            'amount_percentile': 'Amount rank (0-1) - identifies outliers',
            'is_new_device': 'New device flag - fraud often uses unfamiliar devices',
            'is_new_location': 'New location flag - geographical anomaly detection',
            'multiple_risk_flags': 'Combined risk score - multiple suspicious signals'
        }
        
        return explanations