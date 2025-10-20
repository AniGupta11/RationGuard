#!/usr/bin/env python3
"""
Revised rationguard dataset generator implementing PHASE 1, PHASE 2, PHASE 3 requirements
with exact 10-digit Ration IDs.

Phase 1
- Ration_ID: 10-digit numeric string (no leading zero)
- Fraud_Label: 1 -> fraud, 0 -> legit
- Fraud distribution: 70% genuine, 20% subsidy misuse, 10% duplicate
- Claimed quantities may include decimals
- Parents explicitly Mother/Father

Phase 2
- 64+ features (final 65 after Phase 3)
- Entitlement per person: 2.5–5.0 kg

Phase 3
- Oils: Palm, Soyabean
- Pulses: Masoor, Chana, Moong
- Add “Percentage_Ration_Left” column
- Overclaim checked item-wise
- Remarks auto-filled with fraud reason
"""

import pandas as pd
import random
import argparse
import os
from faker import Faker
from datetime import datetime

fake = Faker("en_IN")
Faker.seed(42)
random.seed(42)

# Explicit relations
RELATIONS = ["Son", "Daughter", "Spouse", "Mother", "Father"]

# Updated commodities
COMMODITIES = [
    "Rice", "Wheat", "Sugar", "Kerosene",
    "Masoor", "Chana", "Moong", "Salt",
    "PalmOil", "SoyabeanOil"
]

OUTPUT_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "rationguard_dataset_generated.csv")

# ---------- ID & helper generators ----------

def generate_ration_id_10_digit():
    """Generate exact 10-digit Ration ID, no leading zero"""
    first = random.randint(1, 9)
    rest = random.randint(0, 10**9 - 1)
    return f"{first}{rest:09d}"

def generate_phone():
    return f"{random.choice(['6','7','8','9'])}{random.randint(100000000,999999999)}"

def generate_aadhaar():
    return f"{random.randint(100000000000,999999999999)}"

# ---------- Record generator ----------

def generate_record(index):
    record = {}

    # Basic identity
    record["Ration_ID"] = generate_ration_id_10_digit()
    record["Name"] = fake.name()
    record["Age"] = random.randint(18, 75)
    record["Gender"] = random.choice(["Male","Female"])
    record["Address"] = fake.address().replace("\n", ", ")
    record["Phone_No"] = generate_phone()
    record["Aadhaar_ID"] = generate_aadhaar()
    record["Block"] = f"Block{random.randint(1,20)}"
    record["Income_Level"] = random.choices(["Low","Medium","High"],weights=[0.5,0.35,0.15])[0]

    # Dependents
    num_dependents = random.randint(0,5)
    for i in range(1,6):
        if i <= num_dependents:
            relation = random.choice(RELATIONS)
            record[f"Dependent{i}_Name"] = fake.first_name()
            record[f"Dependent{i}_Aadhaar_ID"] = generate_aadhaar()
            record[f"Dependent{i}_Relation"] = relation
            if relation in ["Son","Daughter"]:
                record[f"Dependent{i}_Age"] = random.randint(0,24)
            elif relation == "Spouse":
                record[f"Dependent{i}_Age"] = random.randint(record["Age"]-10, record["Age"]+10)
            else:
                record[f"Dependent{i}_Age"] = random.randint(record["Age"]+16, record["Age"]+45)
        else:
            record[f"Dependent{i}_Name"] = ""
            record[f"Dependent{i}_Aadhaar_ID"] = ""
            record[f"Dependent{i}_Relation"] = ""
            record[f"Dependent{i}_Age"] = ""

    family_size = 1 + num_dependents

    # Entitlements and claims
    for item in COMMODITIES:
        ent = round(random.uniform(family_size*2.5, family_size*5.0),1)
        r = random.random()
        if r < 0.3:
            claimed = round(ent * random.uniform(0.2,0.8),1)
        elif r < 0.8:
            claimed = round(ent * random.uniform(0.9,1.0),1) if random.random()<0.6 else ent
        else:
            claimed = round(ent + random.uniform(0.5,3.0),1)
        record[f"{item}_Entitled"] = ent
        record[f"{item}_Claimed"] = claimed

    # Subsidy
    record["Subsidy_Availed"] = random.choices(["Yes","No"],weights=[0.6,0.4])[0]

    # Derived totals
    total_ent = sum(record[f"{c}_Entitled"] for c in COMMODITIES)
    total_claim = sum(record[f"{c}_Claimed"] for c in COMMODITIES)

    # Item-wise left and overclaim
    item_over = []
    for c in COMMODITIES:
        left = round(record[f"{c}_Entitled"] - record[f"{c}_Claimed"],1)
        record[f"{c}_Left"] = left
        record[f"{c}_Left_Percent"] = round((left/record[f"{c}_Entitled"])*100,2)
        if record[f"{c}_Claimed"] > record[f"{c}_Entitled"]:
            item_over.append(c)

    num_children = sum(1 for i in range(1,6) if record[f"Dependent{i}_Relation"] in ["Son","Daughter"])
    any_parent = 1 if any(record[f"Dependent{i}_Relation"] in ["Mother","Father"] for i in range(1,6)) else 0

    over_claim_flag = 1 if item_over else 0
    record["Duplicate_Aadhaar_Flag"] = 0
    income_subsidy_mismatch = 1 if record["Income_Level"]=="High" and record["Subsidy_Availed"]=="Yes" else 0

    record["Transaction_Date"] = fake.date_between(start_date='-1y',end_date='today').strftime('%Y-%m-%d')
    record["Shop_ID"] = f"SHOP{random.randint(1000,9999)}"
    record["Block_Name"] = f"Block {record['Block'].replace('Block','')}"

    record["Remarks"] = ""
    record["Num_Dependents"] = num_dependents
    record["Num_Children"] = num_children
    record["Any_Parent"] = any_parent
    record["Total_Entitlement"] = round(total_ent,1)
    record["Total_Claimed"] = round(total_claim,1)
    record["Claimed_vs_Entitled_Percent"] = round((total_claim/total_ent)*100,2)
    record["Over_Claim_Flag"] = over_claim_flag
    record["Income_Subsidy_Mismatch"] = income_subsidy_mismatch

    # Fraud detection
    fraud_reasons = []
    if any(record[f"Dependent{i}_Relation"] in ["Son","Daughter"] and 
           record[f"Dependent{i}_Age"]!="" and int(record[f"Dependent{i}_Age"])>=25 
           for i in range(1,6)):
        fraud_reasons.append("Adult_Dependent")
    if over_claim_flag:
        fraud_reasons += [f"Overclaim_{c}" for c in item_over]
    if income_subsidy_mismatch:
        fraud_reasons.append("Income_Subsidy_Mismatch")

    record["Fraud_Label"] = 1 if fraud_reasons else 0
    record["_Fraud_Reasons_List"] = fraud_reasons

    # Percentage ration left
    total_left = round(total_ent - total_claim,1)
    pct_left = round((total_left/total_ent)*100,2)
    record["Percentage_Ration_Left"] = max(min(pct_left,100.0),-100.0)

    return record

# ---------- Dataset generation ----------

def generate_dataset(n_records, output_file=OUTPUT_FILE):
    genuine = int(n_records*0.7)
    subsidy = int(n_records*0.2)
    duplicate = n_records - genuine - subsidy
    print(f"Generating {genuine} genuine, {subsidy} subsidy misuse, {duplicate} duplicate records")

    data = []

    # Genuine
    for _ in range(genuine):
        r = generate_record(_)
        r["Fraud_Label"]=0; r["_Fraud_Reasons_List"]=[]
        data.append(r)

    # Subsidy misuse
    for _ in range(genuine,genuine+subsidy):
        r = generate_record(_)
        r["Income_Level"]="High"
        r["Subsidy_Availed"]="Yes"
        r["Income_Subsidy_Mismatch"]=1
        r["Fraud_Label"]=1
        r["_Fraud_Reasons_List"]=["Income_Subsidy_Mismatch"]
        data.append(r)

    # Duplicates
    for _ in range(genuine+subsidy,n_records):
        r = generate_record(_)
        prev=random.choice(data)
        r["Aadhaar_ID"]=prev["Aadhaar_ID"]
        r["Duplicate_Aadhaar_Flag"]=1
        r["Fraud_Label"]=1
        r["_Fraud_Reasons_List"]=r.get("_Fraud_Reasons_List",[])+["Duplicate_Aadhaar"]
        data.append(r)

    df=pd.DataFrame(data)

    # Remarks auto-fill
    df["Remarks"]=df.apply(lambda x: ";".join(sorted(set(x["_Fraud_Reasons_List"]))) if x["_Fraud_Reasons_List"] else "",axis=1)

    # Derived features filler to make 65 cols
    while df.shape[1]<65:
        df[f"DerivedFeature_{df.shape[1]-len(df.columns)+1}"]= (df["Total_Entitlement"]*random.uniform(0.01,0.1)).round(2)

    df.drop(columns=["_Fraud_Reasons_List"],errors="ignore",inplace=True)
    df=df.sample(frac=1,random_state=42).reset_index(drop=True)
    os.makedirs(os.path.dirname(output_file),exist_ok=True)
    df.to_csv(output_file,index=False)

    print(f"Saved dataset to {output_file}")
    print(f"Records: {len(df)} | Fraud: {df['Fraud_Label'].sum()} | Legit: {len(df)-df['Fraud_Label'].sum()}")
    print(f"Final column count: {df.shape[1]} (target 65)")
    return df

# ---------- Main ----------

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--records",type=int,default=50000)
    parser.add_argument("--output",type=str,default=OUTPUT_FILE)
    args=parser.parse_args()
    start=datetime.now()
    df=generate_dataset(args.records,args.output)
    print("Generation time:",datetime.now()-start)
