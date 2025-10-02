import pandas as pd
import random
import argparse
import os
from faker import Faker

fake = Faker("en_IN")

# Allowed relations
RELATIONS = ["Son", "Daughter", "Spouse", "Parent"]

# Commodities list
COMMODITIES = [
    "Rice", "Wheat", "Sugar", "Kerosene",
    "ToorDal", "ChanaDal", "UradDal", "Salt",
    "MustardOil", "SunflowerOil"
]

# Hardcoded output path
OUTPUT_FILE = r"D:/RationGuard/Implementation/Data/Raw/rationguard_dataset.csv"

def generate_record(record_id):
    record = {}

    # Household Info
    record["Ration_ID"] = f"RAT{10000+record_id}"
    record["Name"] = fake.name()
    record["Age"] = random.randint(25, 70)
    record["Gender"] = random.choice(["Male", "Female"])
    record["Address"] = fake.address().replace("\n", ", ")
    record["Phone_No"] = fake.msisdn()
    record["Aadhaar_ID"] = str(random.randint(100000000000, 999999999999))
    record["Block"] = f"Block{random.randint(1, 5)}"
    record["Income_Level"] = random.choice(["Low", "Medium", "High"])

    # Dependents (up to 5, but max 3 allowed logically)
    num_dependents = random.randint(0, 5)
    for i in range(1, 6):
        if i <= num_dependents:
            record[f"Dependent{i}_Name"] = fake.first_name()
            record[f"Dependent{i}_Aadhaar_ID"] = str(random.randint(100000000000, 999999999999))
            record[f"Dependent{i}_Relation"] = random.choice(RELATIONS)
            record[f"Dependent{i}_Age"] = random.randint(1, 60)
        else:
            record[f"Dependent{i}_Name"] = ""
            record[f"Dependent{i}_Aadhaar_ID"] = ""
            record[f"Dependent{i}_Relation"] = ""
            record[f"Dependent{i}_Age"] = ""

    # Entitlements & Claims
    for item in COMMODITIES:
        entitlement = random.randint(1, 5)  # entitlement per commodity
        claim = entitlement if random.random() > 0.2 else entitlement + random.randint(1, 3)  # over-claim chance
        record[f"{item}_Entitled"] = entitlement
        record[f"{item}_Claimed"] = claim

    # Subsidy
    record["Subsidy_Availed"] = random.choice(["Yes", "No"])

    # Derived features
    total_entitled = sum([record[f"{c}_Entitled"] for c in COMMODITIES])
    total_claimed = sum([record[f"{c}_Claimed"] for c in COMMODITIES])
    record["Percent_Ration_Left"] = round(((total_entitled - total_claimed) / total_entitled) * 100, 2)
    record["Num_Dependents"] = num_dependents
    record["Over_Claim_Flag"] = 1 if total_claimed > total_entitled else 0
    record["Duplicate_Aadhaar_Flag"] = 0  # will adjust later
    record["Income_Subsidy_Mismatch"] = 1 if record["Income_Level"] == "High" and record["Subsidy_Availed"] == "Yes" else 0

    # Fraud label – basic rules
    fraud = 0
    if num_dependents > 3: fraud = 1
    if any(record[f"Dependent{i}_Age"] and int(record[f"Dependent{i}_Age"]) >= 25 for i in range(1, 6)):
        fraud = 1
    if record["Over_Claim_Flag"] == 1: fraud = 1
    if record["Income_Subsidy_Mismatch"] == 1: fraud = 1
    record["Fraud_Label"] = fraud

    return record

def generate_dataset(n_records):
    dataset = []
    for i in range(n_records):
        dataset.append(generate_record(i))
    df = pd.DataFrame(dataset)

    # Simulate duplicate Aadhaar for fraud
    for _ in range(n_records // 100):  # ~1% duplicates
        idx1, idx2 = random.sample(range(len(df)), 2)
        df.loc[idx2, "Aadhaar_ID"] = df.loc[idx1, "Aadhaar_ID"]
        df.loc[idx2, "Duplicate_Aadhaar_Flag"] = 1
        df.loc[idx2, "Fraud_Label"] = 1

    # Ensure output directory exists
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)

    df.to_csv(OUTPUT_FILE, index=False)
    print(f"✅ Dataset generated: {OUTPUT_FILE} with {n_records} records.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--records", type=int, default=1000, help="Number of records to generate")
    args = parser.parse_args()

    generate_dataset(args.records)
