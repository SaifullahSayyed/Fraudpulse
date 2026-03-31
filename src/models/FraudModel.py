import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import (
    classification_report, 
    confusion_matrix, 
    roc_auc_score,
    precision_recall_curve,
    auc
)
from typing import Dict, List, Tuple, Optional
import pickle
import os

class FraudDetectionModel:
    
    def __init__(self, dataset_type: str = 'creditcard'):
        self.dataset_type = dataset_type
        self.model = None
        self.scaler = StandardScaler()
        self.feature_columns = None
        self.target_column = 'Class' if dataset_type == 'creditcard' else 'isFraud'
        
        self.metrics = {}
        
    def prepare_data(
        self, 
        df: pd.DataFrame, 
        feature_columns: List[str],
        test_size: float = 0.3,
        random_state: int = 42
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        print(" Preparing data for model training...")
        
        self.feature_columns = feature_columns
        
        X = df[feature_columns].copy()
        y = df[self.target_column].copy()
        
        if X.isnull().sum().sum() > 0:
            print("Filling missing values with median...")
            X = X.fillna(X.median())
        
        X_train, X_test, y_train, y_test = train_test_split(
            X, y,
            test_size=test_size,
            random_state=random_state,
            stratify=y
        )
        
        print(f"Train set: {len(X_train):,} transactions")
        print(f"Test set: {len(X_test):,} transactions")
        print(f"Fraud rate in train: {y_train.mean()*100:.2f}%")
        print(f"Fraud rate in test: {y_test.mean()*100:.2f}%")
        
        print(" Scaling features...")
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)
        
        return X_train_scaled, X_test_scaled, y_train.values, y_test.values
    
    def train(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        handle_imbalance: bool = True
    ) -> None:
        print("\n Training Random Forest model...")
        
        class_weight = 'balanced' if handle_imbalance else None
        
        if handle_imbalance:
            fraud_count = y_train.sum()
            legit_count = len(y_train) - fraud_count
            print(f"Using balanced class weights")
        
        self.model = RandomForestClassifier(
            n_estimators=100,        
            max_depth=20,            
            min_samples_split=10,    
            min_samples_leaf=5,      
            class_weight=class_weight,
            random_state=42,
            n_jobs=-1,               
            verbose=0
        )
        
        print(f"  Growing forest of {100} trees...")
        self.model.fit(X_train, y_train)
        print("  Model training complete!")
        
        self._calculate_feature_importance()
    
    def _calculate_feature_importance(self) -> None:
        if self.model is None or self.feature_columns is None:
            return
        
        importances = self.model.feature_importances_
        
        feature_importance = sorted(
            zip(self.feature_columns, importances),
            key=lambda x: x[1],
            reverse=True
        )
        
        print("\n Top 5 Most Important Features:")
        for i, (feature, importance) in enumerate(feature_importance[:5], 1):
            print(f"  {i}. {feature}: {importance:.4f}")
        
        self.feature_importance = dict(feature_importance)
    
    def evaluate(
        self,
        X_test: np.ndarray,
        y_test: np.ndarray
    ) -> Dict:
        print("\n Evaluating model performance...")
        
        y_pred = self.model.predict(X_test)
        y_pred_proba = self.model.predict_proba(X_test)[:, 1]  
        
        tn, fp, fn, tp = confusion_matrix(y_test, y_pred).ravel()
        
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0
        f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
        
        roc_auc = roc_auc_score(y_test, y_pred_proba)
        
        precision_curve, recall_curve, _ = precision_recall_curve(y_test, y_pred_proba)
        pr_auc = auc(recall_curve, precision_curve)
        
        self.metrics = {
            'true_positives': int(tp),
            'false_positives': int(fp),
            'true_negatives': int(tn),
            'false_negatives': int(fn),
            'precision': float(precision),
            'recall': float(recall),
            'f1_score': float(f1),
            'roc_auc': float(roc_auc),
            'pr_auc': float(pr_auc),
            'accuracy': float((tp + tn) / (tp + tn + fp + fn))
        }
        
        print("\n" + "="*60)
        print(" MODEL PERFORMANCE METRICS")
        print("="*60)
        print(f"Accuracy: {self.metrics['accuracy']:.4f}")
        print(f"Precision: {self.metrics['precision']:.4f}")
        print(f"Recall: {self.metrics['recall']:.4f}")
        print(f"F1-Score: {self.metrics['f1_score']:.4f}")
        print(f"ROC-AUC: {self.metrics['roc_auc']:.4f}")
        print(f"PR-AUC: {self.metrics['pr_auc']:.4f}")
        print("\n Confusion Matrix:")
        print(f"  True Negatives: {tn:,}")
        print(f"  False Positives: {fp:,} (legit flagged as fraud)")
        print(f"  False Negatives: {fn:,} (fraud missed)")
        print(f"  True Positives: {tp:,} (fraud caught!)")
        print("="*60)
        
        return self.metrics
    
    def predict_fraud_score(
        self,
        transaction_features: Dict
    ) -> Tuple[float, Dict]:
        if self.model is None:
            raise ValueError("Model not trained yet! Call train() first.")
        
        df = pd.DataFrame([transaction_features])
        
        missing_features = set(self.feature_columns) - set(df.columns)
        if missing_features:
            raise ValueError(f"Missing features: {missing_features}")
        
        X = df[self.feature_columns].values
        
        X_scaled = self.scaler.transform(X)
        
        fraud_probability = self.model.predict_proba(X_scaled)[0, 1]
        
        return fraud_probability, transaction_features
    
    def save_model(self, filepath: str = 'models/fraud_model.pkl') -> None:
        filepath = os.path.abspath(filepath)
        
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        model_data = {
            'model': self.model,
            'scaler': self.scaler,
            'feature_columns': self.feature_columns,
            'dataset_type': self.dataset_type,
            'metrics': self.metrics
        }
        
        with open(filepath, 'wb') as f:
            pickle.dump(model_data, f)
        
        print(f" Model saved to: {filepath}")
    
    def load_model(self, filepath: str = 'models/fraud_model.pkl') -> None:
        filepath = os.path.abspath(filepath)
        with open(filepath, 'rb') as f:
            model_data = pickle.load(f)
        
        self.model = model_data['model']
        self.scaler = model_data['scaler']
        self.feature_columns = model_data['feature_columns']
        self.dataset_type = model_data['dataset_type']
        self.metrics = model_data.get('metrics', {})
        
        print(f"Model loaded from: {filepath}")