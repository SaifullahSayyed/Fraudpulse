import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.ingestion.DataLoader import DataLoader
import pandas as pd

def test_with_sample_data():
    print("=" * 60)
    print("TEST: Data Loader")
    print("=" * 60)
    
    print("\nCreating sample data file...")
    
    sample_data = {
        'transaction_id': ['TXN001', 'TXN002', 'TXN003'],
        'amount': [50.00, 5000.00, 25.00],
        'merchant_category': ['groceries', 'electronics', 'restaurant'],
        'location': ['New York', 'Los Angeles', 'New York'],
        'user_location': ['New York', 'New York', 'New York'],
        'time': ['14:30', '02:00', '18:45'],
        'card_present': [True, False, True],
        'is_fraud': [0, 1, 0]
    }
    
    df_sample = pd.DataFrame(sample_data)
    
    os.makedirs('data', exist_ok=True)
    
    sample_file = 'data/sample_transactions.csv'
    df_sample.to_csv(sample_file, index=False)
    print(f"Created: {sample_file}")
    
    print("\nTesting DataLoader")
    
    try:
        
        loader = DataLoader()
        
        df = loader.load_data(sample_file)
        
        print("\nData Information:")
        info = loader.get_data_info(df)
        for key, value in info.items():
            print(f"  • {key}: {value}")
        
        print("\n First 3 rows of data:")
        print(df.head(3))
        
        print("\nTEST PASSED!")
        
    except Exception as e:
        print(f"\nTEST FAILED: {str(e)}")
        return False
    
    return True

def test_missing_file():
    print("\n" + "=" * 60)
    print("TEST: Missing File Error Handling")
    print("=" * 60)
    
    loader = DataLoader()
    
    try:
        loader.load_data('data/nonexistent.csv')
        print("TEST FAILED: Should have raised FileNotFoundError")
    except FileNotFoundError as e:
        print(f"Correctly caught missing file error:")
        print(f"   {str(e)}")

def test_missing_columns():
    print("\n" + "=" * 60)
    print("TEST: Missing Columns Error Handling")
    print("=" * 60)
    
    incomplete_data = pd.DataFrame({
        'transaction_id': ['TXN001'],
        'amount': [50.00]
        
    })
    
    test_file = 'data/incomplete_data.csv'
    incomplete_data.to_csv(test_file, index=False)
    
    loader = DataLoader()
    
    try:
        loader.load_data(test_file)
        print(" TEST FAILED: Should have raised ValueError")
    except ValueError as e:
        print(f" Correctly caught missing columns error:")
        print(f"   {str(e)[:100]}...")  

if __name__ == "__main__":
    print("\ntarting Data Loader Tests\n")
    
    test_with_sample_data()
    test_missing_file()
    test_missing_columns()
    
    print("\n" + "=" * 60)
    print(" All tests completed!")
    print("=" * 60)