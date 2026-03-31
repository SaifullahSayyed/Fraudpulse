import sys
import os
import pandas as pd
import numpy as np

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.ingestion.DataLoader import DataLoader
from src.features.FeatureEngineering import FeatureEngineer
from src.models.FraudModel import FraudDetectionModel
from src.orchestration.manager import process_transaction

def run_complete_pipeline():
    print("\n" + "="*70)
    print("FRAUDPULSE - DATA PIPELINE")
    print("="*70)
    
    print("\nDATA INGESTION")
    print("-" * 70)
    
    loader = DataLoader(dataset_type='creditcard')
    
    try:
        df = loader.load_data('data/raw/creditcard.csv')
    except FileNotFoundError:
        print("\nError: creditcard.csv not found in data/raw/")
        print("Please download the dataset from:")
        print("https://www.kaggle.com/mlg-ulb/creditcardfraud")
        print("And place it in: data/raw/creditcard.csv")
        return
    
    stats = loader.get_fraud_statistics(df)
    
    print("\n FEATURE ENGINEERING")
    print("-" * 70)
    
    engineer = FeatureEngineer(dataset_type='creditcard')
    
    df_features = engineer.engineer_features(df)
    
    feature_columns = engineer.get_feature_list()
    
    v_features = [col for col in df.columns if col.startswith('V')]
    all_features = feature_columns + v_features
    
    print(f"\n Total features for model: {len(all_features)}")
    print(f"  • Engineered features: {len(feature_columns)}")
    print(f"  • Original V features: {len(v_features)}")
    
    print("\n MODEL TRAINING")
    print("-" * 70)
    
    model = FraudDetectionModel(dataset_type='creditcard')
    
    X_train, X_test, y_train, y_test = model.prepare_data(
        df_features,
        feature_columns=all_features,
        test_size=0.3,
        random_state=42
    )
    
    model.train(X_train, y_train, handle_imbalance=True)
    
    metrics = model.evaluate(X_test, y_test)
    
    model.save_model('models/fraud_model.pkl')
    
    print("\n SAMPLE PREDICTION")
    print("-" * 70)
    
    sample_transaction = create_sample_transaction(df_features, all_features, suspicious=True)
    
    print("\n Sample Transaction Features:")
    print("-" * 70)
    for feature, value in sample_transaction.items():
        if not feature.startswith('V'):  
            print(f"  • {feature}: {value}")
    
    fraud_score, features_used = model.predict_fraud_score(sample_transaction)
    
    print("\n" + "="*70)
    print("PREDICTION RESULT")
    print("="*70)
    print(f"\nFraud Score: {fraud_score:.4f} ({fraud_score*100:.2f}%)")
    
    print("\n" + "="*70)
    print("ROUTING TO DECISION INTELLIGENCE AGENTS")
    print("="*70)
    
    import json
    
    agent_result = process_transaction(
        transaction_id="TX_DEMO_SAMPLE",
        amount=sample_transaction.get("Amount", sample_transaction.get("amount", 0.0)),
        merchant="Demo Machine Learning System",
        fraud_score=fraud_score,
        user_id="U_DEMO_123"
    )
    
    print(f"\nPipeline Complete! Output from Escalation Agent:")
    print(json.dumps(agent_result, indent=2))
    
    print("\n" + "="*70)
    print(" PIPELINE EXECUTION COMPLETE")
    print("="*70)
    
    print("\n PIPELINE SUMMARY:")
    print(f"  • Total transactions processed: {len(df):,}")
    print(f"  • Features engineered: {len(feature_columns)}")
    print(f"  • Model accuracy: {metrics['accuracy']:.4f}")
    print(f"  • Model precision: {metrics['precision']:.4f}")
    print(f"  • Model recall: {metrics['recall']:.4f}")
    print(f"  • Model saved: models/fraud_model.pkl")
    print("\nPipeline execution finished.\n")

def create_sample_transaction(df: pd.DataFrame, feature_columns: list, suspicious: bool = True):
    
    sample = df[df['Class'] == 0].sample(1).iloc[0]
    
    transaction = {}
    for col in feature_columns:
        if col in sample.index:
            transaction[col] = sample[col]
    
    if suspicious:
        transaction['is_high_amount'] = 1
        transaction['is_night_transaction'] = 1
        transaction['transaction_hour'] = 2  
        transaction['is_new_device'] = 1
        transaction['is_new_location'] = 1
        transaction['multiple_risk_flags'] = 1
        transaction['amount_normalized'] = 6.5  
    
    return transaction

def demo_prediction_on_real_data():
    print("\n" + "="*70)
    print("BONUS: PREDICTIONS ON REAL TRANSACTIONS")
    print("="*70)
    
    model = FraudDetectionModel()
    try:
        model.load_model('models/fraud_model.pkl')
    except FileNotFoundError:
        print(" Model not found. Run main pipeline first.")
        return
    
    loader = DataLoader(dataset_type='creditcard')
    df = loader.load_data('data/raw/creditcard.csv')
    
    engineer = FeatureEngineer(dataset_type='creditcard')
    df_features = engineer.engineer_features(df)
    
    feature_columns = engineer.get_feature_list()
    v_features = [col for col in df.columns if col.startswith('V')]
    all_features = feature_columns + v_features
    
    fraud_transactions = df_features[df_features['Class'] == 1].head(5)
    
    print("\n Testing on 5 ACTUAL FRAUDULENT transactions:")
    print("-" * 70)
    
    for idx, (_, row) in enumerate(fraud_transactions.iterrows(), 1):
        
        features = {col: row[col] for col in all_features}
        
        score, _ = model.predict_fraud_score(features)
        
        agent_result = process_transaction(
            transaction_id=f"TX_FRAUD_{idx}",
            amount=row['Amount'],
            merchant="Real Dataset Demo",
            fraud_score=score,
            user_id="U_DEMO_REAL"
        )
        
        print(f"\nFraud #{idx}:")
        print(f"  Amount: ${row['Amount']:.2f}")
        print(f"  Hour: {int(row['transaction_hour']):02d}:00")
        print(f"  Predicted Score: {score:.4f} ({score*100:.1f}%)")
        print(f"  Agent Decision: {agent_result.get('final_decision')}")
    
    legit_transactions = df_features[df_features['Class'] == 0].sample(5)
    
    print("\n\nTesting on 5 LEGITIMATE transactions:")
    print("-" * 70)
    
    for idx, (_, row) in enumerate(legit_transactions.iterrows(), 1):
        features = {col: row[col] for col in all_features}
        score, _ = model.predict_fraud_score(features)
        
        agent_result = process_transaction(
            transaction_id=f"TX_LEGIT_{idx}",
            amount=row['Amount'],
            merchant="Real Dataset Demo",
            fraud_score=score,
            user_id="U_DEMO_REAL"
        )
        
        print(f"\nLegit #{idx}:")
        print(f"  Amount: ${row['Amount']:.2f}")
        print(f"  Hour: {int(row['transaction_hour']):02d}:00")
        print(f"  Predicted Score: {score:.4f} ({score*100:.1f}%)")
        print(f"  Agent Decision: {agent_result.get('final_decision')}")

if __name__ == "__main__":
    
    run_complete_pipeline()
    
    print("\n\n")
    response = input("Would you like to see predictions on real transactions? (y/n): ")
    if response.lower() == 'y':
        demo_prediction_on_real_data()