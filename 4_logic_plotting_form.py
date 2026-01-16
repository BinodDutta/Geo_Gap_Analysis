import pandas as pd
import numpy as np
import glob
import os
from sklearn.preprocessing import StandardScaler

# ---------------- CONFIG ----------------
BASE_PATH = "Cleaned_Data"
FOLDERS = {
    "enrol": os.path.join(BASE_PATH, "Enrolment"),
    "demo": os.path.join(BASE_PATH, "Demographics"),
    "bio": os.path.join(BASE_PATH, "Biometric"),
    "camp": os.path.join(BASE_PATH, "Campaigns")
}

# Category Weights (Service Importance)
CAT_WEIGHTS = {"enrol": 1.0, "demo": 1.2, "bio": 2.5}
EMA_ALPHA = 0.4  

MONTH_MAP = {
    "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6,
    "july": 7, "august": 8, "september": 9, "october": 10, "november": 11, "december": 12
}

# ---------------- FAST HELPERS ----------------
def clean_numeric(series):
    return pd.to_numeric(series, errors='coerce').fillna(0)

def load_and_prep_weighted(folder, cat_weight, col_weights):
    """
    Reads files and applies specific weights to specific columns (Age Priority).
    col_weights = {'age_0_5': 1.5, 'age_5_17': 1.2, ...}
    """
    files = glob.glob(os.path.join(folder, "*.csv"))
    if not files: return pd.DataFrame()
    
    try:
        df = pd.concat((pd.read_csv(f, dtype=str) for f in files if "master" not in f), ignore_index=True)
    except ValueError: return pd.DataFrame()

    if df.empty: return pd.DataFrame()

    df.columns = df.columns.str.strip()
    
    if 'Month' in df.columns:
        df['Month'] = df['Month'].astype(str).str.lower().str.strip().map(MONTH_MAP)
        df = df.dropna(subset=['Month'])
    
    if 'pincode' in df.columns:
        df['pincode'] = df['pincode'].astype(str).str.split('.').str[0].str.strip()
    
    # --- AGE WEIGHTING HAPPENS HERE ---
    total_vol = 0
    for col, age_weight in col_weights.items():
        if col in df.columns:
            # Multiply count by Age Priority (1.5, 1.2, or 1.0)
            total_vol += clean_numeric(df[col]) * age_weight
            
    # Then multiply by Category Priority (Service Type)
    df['partial_load'] = total_vol * cat_weight
    return df[['Month', 'pincode', 'partial_load']]

def load_campaigns_fast(folder):
    files = glob.glob(os.path.join(folder, "*.csv"))
    if not files: return pd.DataFrame()
    try:
        df = pd.concat((pd.read_csv(f, dtype=str) for f in files), ignore_index=True)
        if df.empty: return pd.DataFrame()
        df.columns = df.columns.str.strip()
        if 'pincode' in df.columns:
            df['pincode'] = df['pincode'].astype(str).str.split('.').str[0].str.strip()
        col_name = 'campaigns_count' if 'campaigns_count' in df.columns else df.columns[1]
        df['camp_count'] = clean_numeric(df[col_name])
        return df.groupby('pincode', as_index=False)['camp_count'].sum()
    except: return pd.DataFrame()

# ---------------- EXECUTION ----------------
print(">>> Fast Loading with Age Priorities...")

# 1. Enrolment Config
enrol_cols = {
    'age_0_5': 1.5,        # Infant Priority
    'age_5_17': 1.2,       # Child Priority
    'age_18_greater': 1.0  # Adult
}
df_enrol = load_and_prep_weighted(FOLDERS["enrol"], CAT_WEIGHTS["enrol"], enrol_cols)

# 2. Demographics Config
demo_cols = {
    'demo_age_5_17': 1.2,  # Child
    'demo_age_17_': 1.0    # Adult
}
df_demo = load_and_prep_weighted(FOLDERS["demo"], CAT_WEIGHTS["demo"], demo_cols)

# 3. Biometric Config
bio_cols = {
    'bio_age_5_17': 1.2,   # Child (MBU)
    'bio_age_17_': 1.0     # Adult
}
df_bio = load_and_prep_weighted(FOLDERS["bio"], CAT_WEIGHTS["bio"], bio_cols)

print(">>> Turbo Merging...")
combined = pd.concat([df_enrol, df_demo, df_bio], ignore_index=True)
final_df = combined.groupby(['pincode', 'Month'], as_index=False)['partial_load'].sum()
final_df.rename(columns={'partial_load': 'raw_load'}, inplace=True)

# ---------------- SUPPLY ADJUSTMENT ----------------
print(">>> Applying Supply Logic (3 + 1.25*Camp)...")

df_camps = load_campaigns_fast(FOLDERS["camp"])

if not df_camps.empty:
    final_df = pd.merge(final_df, df_camps, on='pincode', how='left')
    final_df['camp_count'] = final_df['camp_count'].fillna(0)
    final_df['net_load'] = final_df['raw_load'] / (3 + (1.25 * final_df['camp_count']))
else:
    print("   (No campaign data. Using baseline.)")
    final_df['net_load'] = final_df['raw_load'] / 3

# ---------------- EMA & STATISTICS ----------------
print(">>> Calculating Statistics...")

final_df = final_df.sort_values(['pincode', 'Month'])

final_df['ema_load'] = (
    final_df
    .groupby('pincode')['net_load']
    .transform(lambda x: x.ewm(alpha=EMA_ALPHA, adjust=False).mean())
)

scaler = StandardScaler()
final_df['z_score'] = scaler.fit_transform(final_df[['ema_load']])

def assign_severity(z):
    if z >= 3.0: return "Extreme"
    if z >= 2.0: return "Critical"
    if z >= 1.0: return "High"
    return "Moderate"

critical_zones = final_df[final_df['z_score'] > 0].copy()
critical_zones['severity'] = critical_zones['z_score'].apply(assign_severity)

critical_zones = (
    critical_zones
    .sort_values(['pincode', 'Month'])
    .drop_duplicates('pincode', keep='last')
    .sort_values('z_score', ascending=False)
)

# ---------------- EXPORT ----------------
output_file = os.path.join(BASE_PATH, "statistical_gap_analysis.json")
critical_zones.to_json(output_file, orient="records", indent=4)

print(f">>> SUCCESS! {len(critical_zones)} zones exported with Age Priority + Campaign Logic.")