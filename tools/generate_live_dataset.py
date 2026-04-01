import csv
import random
import uuid

NEW_YORK = (40.7128, -74.0060)
LONDON = (51.5074, -0.1278)
MUMBAI = (19.0760, 72.8777)

def generate_live_dataset(filename="data/live_transaction_stream.csv"):
    with open(filename, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([
            "account_id", "receiver_id", "amount", "latitude", "longitude", 
            "device_id", "is_known_device", "transaction_hour", "is_foreign_transaction", "ml_fraud_score"
        ])
        
        for _ in range(10):
            writer.writerow([
                f"ACC_{random.randint(100,200)}", f"REC_{random.randint(100,200)}", round(random.uniform(10, 200), 2),
                NEW_YORK[0] + random.uniform(-0.1, 0.1), NEW_YORK[1] + random.uniform(-0.1, 0.1),
                f"DEV_KNOWN", True, random.randint(8, 20), False, round(random.uniform(0.01, 0.15), 3)
            ])
            
        acc_traveller = "ACC_IMP_TRAVELLER"
        writer.writerow([acc_traveller, "REC_XYZ", 450.00, NEW_YORK[0], NEW_YORK[1], "DEV_KNOWN", True, 10, False, 0.12])
        writer.writerow([acc_traveller, "REC_XYZ", 3000.00, LONDON[0], LONDON[1], "DEV_UNKNOWN", False, 10, True, 0.88])
        
        acc_velocity = "ACC_VEL_BOT"
        for _ in range(5):
            writer.writerow([
                acc_velocity, f"REC_MERCHANT", 1500.00,
                MUMBAI[0], MUMBAI[1],
                "DEV_SPOOF", False, 3, False, 0.75
            ])
            
        mule_chain = ["MULE_A", "MULE_B", "MULE_C", "MULE_D"]
        for i in range(len(mule_chain)-1):
            writer.writerow([
                mule_chain[i], mule_chain[i+1], 9800.00,
                LONDON[0], LONDON[1], "DEV_KNOWN", True, 14, False, 0.65
            ])

if __name__ == "__main__":
    generate_live_dataset()
    print("Dataset generated successfully at data/live_transaction_stream.csv")