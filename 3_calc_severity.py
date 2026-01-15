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

WEIGHTS = {"enrol": 1.0, "demo": 1.2, "bio": 2.5}

def find_pincode_column(df):
    """
    Robustly finds the column containing 6-digit Pincodes.
    """
    for col in df.columns:
        try:
            # 1. Convert column to string Series
            s = df[col].astype(str)
            
            # 2. Remove non-digits (vectorized)
            clean_s = s.str.replace(r'\D', '', regex=True)
            
            # 3. Check for 6-digit pattern
            # We check if > 10% of non-empty rows look like pincodes
            valid_mask = clean_s.str.fullmatch(r'\d{6}')
            valid_count = valid_mask.sum()
            total_rows = len(df)
            
            if total_rows > 0 and (valid_count / total_rows) > 0.1:
                return col
        except Exception:
            continue
            
    return None

def fast_process_nuclear(folder_path, col_name):
    print(f"Scanning {folder_path}...")
    files = glob.glob(os.path.join(folder_path, "*.csv"))
    
    if not files: 
        print(f"  [WARN] No files in {folder_path}")
        return pd.DataFrame() # Return empty if no files

    chunk_list = []
    
    for f in files:
        try:
            # 1. READ AGGRESSIVELY
            try:
                # Read everything as string to avoid type errors
                df = pd.read_csv(f, on_bad_lines='skip', encoding='utf-8', dtype=str)
            except UnicodeDecodeError:
                df = pd.read_csv(f, on_bad_lines='skip', encoding='latin1', dtype=str)
            
            if df.empty: continue

            # 2. FIND PINCODE COLUMN
            target_col = find_pincode_column(df)
            
            if target_col is None:
                # print(f"  [SKIP] No pincode data in {os.path.basename(f)}")
                continue

            # 3. NORMALIZE
            # Rename detected column to 'pincode'
            df = df.rename(columns={target_col: 'pincode'})
            
            # Clean and Filter
            df['pincode'] = (
                df['pincode']
                .astype(str)
                .str.split('.').str[0]
                .str.replace(r'\D', '', regex=True)
            )
            df = df[df['pincode'].str.len() == 6]
            
            # 4. AGGREGATE
            chunk_agg = df['pincode'].value_counts().reset_index()
            chunk_agg.columns = ['pincode', col_name]
            chunk_list.append(chunk_agg)
            
        except Exception as e:
            print(f"  [CRASH] File {os.path.basename(f)} failed: {e}")
            continue

    if not chunk_list: 
        return pd.DataFrame(columns=['pincode', col_name]) # Return empty DF with correct columns
        
    return pd.concat(chunk_list).groupby('pincode')[col_name].sum().reset_index()

# --- EXECUTION ---
print(">>> Step 1: Extraction...")
df_enrol = fast_process_nuclear(FOLDERS["enrolment"], "count_enrol")
df_demo = fast_process_nuclear(FOLDERS["demographics"], "count_demo")
df_bio = fast_process_nuclear(FOLDERS["biometric"], "count_bio")

# --- SAFE MERGE ---
print(">>> Step 2: Merging...")

# Helper to ensure DF has 'pincode' column before merging
def validate_df(df, name):
    if 'pincode' not in df.columns:
        return pd.DataFrame(columns=['pincode', name])
    return df

df_enrol = validate_df(df_enrol, "count_enrol")
df_demo = validate_df(df_demo, "count_demo")
df_bio = validate_df(df_bio, "count_bio")

# Start Merge
merged = pd.merge(df_enrol, df_demo, on='pincode', how='outer')
merged = pd.merge(merged, df_bio, on='pincode', how='outer')
merged.fillna(0, inplace=True)

if merged.empty:
    print("FATAL ERROR: No valid Pincode data was found in any folder.")
    exit()

# --- STATISTICAL FILTERING ---
print(">>> Step 3: Statistical Analysis...")

# Weighted Load
merged['raw_load'] = (
    (merged['count_enrol'] * WEIGHTS['enrol']) + 
    (merged['count_demo'] * WEIGHTS['demo']) + 
    (merged['count_bio'] * WEIGHTS['bio'])
) / 3

# Normalize
scaler = StandardScaler()
merged['z_score'] = scaler.fit_transform(merged[['raw_load']])

# Filter Positive Deviations
critical_zones = merged[merged['z_score'] > 0].copy()

# Severity
def assign_severity(z):
    if z >= 3.0: return "Extreme"
    if z >= 2.0: return "Critical"
    if z >= 1.0: return "High"
    return "Moderate"

critical_zones['severity'] = critical_zones['z_score'].apply(assign_severity)
critical_zones = critical_zones.sort_values(by='z_score', ascending=False)

output_file = "Cleaned_Data/statistical_gap_analysis.json"
critical_zones.to_json(output_file, orient='records', indent=4)
print(f"\n>>> SUCCESS! Exported {len(critical_zones)} zones to {output_file}")