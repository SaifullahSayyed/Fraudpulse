import pandas as pd
import os
from typing import Optional, List, Dict
import warnings
warnings.filterwarnings('ignore')

class DataLoader:
    
    def __init__(self, dataset_type: str = 'creditcard'):
        self.dataset_type = dataset_type
        
        self.required_columns = {
            'creditcard': ['Time', 'Amount', 'Class'],
            'paysim': ['step', 'type', 'amount', 'oldbalanceOrg', 'newbalanceOrig', 'isFraud']
        }
        
    def load_data(self, file_path: str) -> pd.DataFrame:
        
        file_path = os.path.abspath(file_path)
        if not os.path.exists(file_path):
            raise FileNotFoundError(
                f" Dataset not found at: {file_path}\n"
                f"Please ensure the file exists in the data/raw/ directory."
            )
        
        try:
            print(f"Loading {self.dataset_type} dataset from: {file_path}")
            df = pd.read_csv(file_path)
            print(f"Loaded {len(df):,} transactions")
        except Exception as e:
            raise Exception(f" Error reading CSV: {str(e)}")
        
        self._validate_columns(df)
        
        df = self._clean_data(df)
        
        self._display_summary(df)
        
        return df
    
    def _validate_columns(self, df: pd.DataFrame) -> None:
        required = self.required_columns.get(self.dataset_type, [])
        actual_columns = set(df.columns)
        required_set = set(required)
        
        missing = required_set - actual_columns
        
        if missing:
            raise ValueError(
                f"Missing required columns: {missing}\n"
                f"Expected: {required}\n"
                f"Found: {list(df.columns)}"
            )
        
        print(f"All required columns present: {required}")
    
    def _clean_data(self, df: pd.DataFrame) -> pd.DataFrame:
        
        initial_rows = len(df)
        df = df.drop_duplicates()
        removed = initial_rows - len(df)
        if removed > 0:
            print(f"Removed {removed} duplicate transactions")
        
        missing_count = df.isnull().sum().sum()
        if missing_count > 0:
            print(f"Found {missing_count} missing values")
            
            df = df.dropna()
            print("Removed rows with missing values")
        
        return df
    
    def _display_summary(self, df: pd.DataFrame) -> None:
        print("\n" + "="*60)
        print("DATASET SUMMARY")
        print("="*60)
        
        print(f"Total Transactions: {len(df):,}")
        print(f"Number of Features: {len(df.columns)}")
        
        fraud_col = 'Class' if self.dataset_type == 'creditcard' else 'isFraud'
        
        if fraud_col in df.columns:
            fraud_count = df[fraud_col].sum()
            legit_count = len(df) - fraud_count
            fraud_pct = (fraud_count / len(df)) * 100
            
            print(f"\nFraudulent: {fraud_count:,} ({fraud_pct:.2f}%)")
            print(f"Legitimate: {legit_count:,} ({100-fraud_pct:.2f}%)")
            print(f"Imbalance Ratio: 1:{legit_count/max(fraud_count, 1):.0f}")
        
        memory_mb = df.memory_usage(deep=True).sum() / 1024**2
        print(f"\nMemory Usage: {memory_mb:.2f} MB")
        print("="*60 + "\n")
    
    def get_fraud_statistics(self, df: pd.DataFrame) -> Dict:
        fraud_col = 'Class' if self.dataset_type == 'creditcard' else 'isFraud'
        
        if fraud_col not in df.columns:
            return {}
        
        fraud_count = df[fraud_col].sum()
        total = len(df)
        
        stats = {
            'total_transactions': total,
            'fraud_count': int(fraud_count),
            'legitimate_count': int(total - fraud_count),
            'fraud_percentage': round((fraud_count / total) * 100, 2),
            'imbalance_ratio': round((total - fraud_count) / max(fraud_count, 1), 2)
        }
        
        return stats    