import pandas as pd
import numpy as np
import glob
import os
from sklearn.preprocessing import StandardScaler

# --- CONFIGURATION ---
FOLDERS = {
    "enrolment": "Cleaned_Data/Enrolment",
    "demographics": "Cleaned_Data/Demographics",
    "biometric": "Cleaned_Data/Biometric"
}

MONTH_WEIGHTS = {
    "December": 1.00, "November": 0.75, "October": 0.56, "September": 0.42,
    "August": 0.32,   "July": 0.24,     "June": 0.18,    "May": 0.13, 
    "April": 0.10,    "March": 0.08,    "February": 0.06, "January": 0.04,
    # Short forms
    "Dec": 1.00, "Nov": 0.75, "Oct": 0.56, "Sep": 0.42,
    "Aug": 0.32, "Jul": 0.24, "Jun": 0.18, "May": 0.13, 
    "Apr": 0.10, "Mar": 0.08, "Feb": 0.06, "Jan": 0.04
}

def clean_pincode(df):
    if 'pincode' not in df.columns: return df
    df['pincode'] = df['pincode'].astype(str).str.split('.').str[0].str.replace(r'\D', '', regex=True)
    return df[df['pincode'].str.len() == 6]

def load_and_score(folder, f_type):
    print(f"Processing {f_type}...")
    files = glob.glob(os.path.join(folder, "*.csv"))
    chunk_list = []

    for f in files:
        try:
            df = pd.read_csv(f, on_bad_lines='skip', dtype=str)
            df = clean_pincode(df)
            
            # Numeric conversion
            cols_to_convert = [col for col in df.columns if 'age' in col.lower()]
            for c in cols_to_convert:
                df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0)

            # --- CALCULATE SCORE ---
            if f_type == "enrolment":
                c0_5 = df.get('age_0_5', 0)
                c5_17 = df.get('age_5_17', 0)
                c18 = df.get('age_18_greater', 0)
                df['score'] = (1.5 * c0_5) + (1.2 * c5_17) + (1.0 * c18)

            elif f_type == "biometric":
                c5_17 = df.get('bio_age_5_17', 0)
                c17_ = df.get('bio_age_17_', 0)
                df['score'] = (1.5 * c5_17) + (1.2 * c17_)

            elif f_type == "demographics":
                c5_17 = df.get('demo_age_5_17', 0)
                c17_ = df.get('demo_age_17_', 0)
                df['score'] = (1.5 * c5_17) + (1.2 * c17_)

            # --- NEW: COUNT TRANSACTIONS ---
            # Every row in the CSV is treated as 1 transaction instance
            df['txn_count'] = 1

            if 'Month' in df.columns:
                chunk_list.append(df[['pincode', 'Month', 'score', 'txn_count']])
            else:
                print(f" [WARN] 'Month' column missing in {os.path.basename(f)}")
                
        except Exception as e:
            print(f" [ERR] {e}")

    if not chunk_list: return pd.DataFrame()
    
    combined = pd.concat(chunk_list)
    
    # Sum both Score AND Transaction Count
    return combined.groupby(['pincode', 'Month'])[['score', 'txn_count']].sum().reset_index()

# --- STEP 1: CALCULATE SCORES & COUNTS ---
# Rename columns to identify source (E, B, D)
df_E = load_and_score(FOLDERS["enrolment"], "enrolment").rename(columns={'score': 'Et', 'txn_count': 'Count_E'})
df_B = load_and_score(FOLDERS["biometric"], "biometric").rename(columns={'score': 'Bt', 'txn_count': 'Count_B'})
df_D = load_and_score(FOLDERS["demographics"], "demographics").rename(columns={'score': 'Dt', 'txn_count': 'Count_D'})

# --- STEP 2: MERGE ---
print(">>> Merging Datasets...")
merged = pd.merge(df_E, df_B, on=['pincode', 'Month'], how='outer')
merged = pd.merge(merged, df_D, on=['pincode', 'Month'], how='outer')
merged.fillna(0, inplace=True)

# --- STEP 3: CALCULATE CORRECTED Nt ---
# Nt = Sum of all transaction counts across datasets for this month
merged['Nt'] = merged['Count_E'] + merged['Count_B'] + merged['Count_D']

# --- STEP 4: RAW LOAD CALCULATION ---
# Formula: (1*Et + 1.2*Dt + 1.5*Bt) / (3 + 1/3 * Nt)
numerator = (1.0 * merged['Et']) + (1.2 * merged['Dt']) + (1.5 * merged['Bt'])
denominator = 3.0 + (merged['Nt'] / 3.0)

merged['raw_load_t'] = numerator / denominator

# --- STEP 5: EMA CALCULATION ---
print(">>> Applying EMA Weights...")
merged['Wt'] = merged['Month'].map(MONTH_WEIGHTS).fillna(1)
merged['weighted_load'] = merged['raw_load_t'] * merged['Wt']

final_ema = merged.groupby('pincode')['weighted_load'].sum().reset_index()
final_ema.rename(columns={'weighted_load': 'EMA_i'}, inplace=True)

# --- STEP 6: Z-SCORE ---
print(">>> Calculating Z-Scores...")
scaler = StandardScaler()
final_ema['z_score'] = scaler.fit_transform(final_ema[['EMA_i']])

# --- EXPORT ---
output_path = "Cleaned_Data/statistical_gap_analysis.json"
final_ema = final_ema.sort_values('z_score', ascending=False)
final_ema.to_json(output_path, orient='records', indent=4)

print(f"\n>>> COMPLETE. Processed {len(final_ema)} pincodes.")
print(f">>> Max Transaction Count (Nt) Observed: {merged['Nt'].max()}")