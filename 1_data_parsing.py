import pandas as pd
import os
import glob

# --- 1. CONFIGURATION ---
input_folders = ["Biometric", "Demographics", "Enrolment"]
output_base_folder = "Cleaned_Data"
raw_base_folder = "raw_data"  # <--- NEW: Define where the raw files live

# --- 2. THE CLEANING LOGIC (Unchanged) ---
def clean_dataset(df):
    # A. DATE HANDLING
    date_col = None
    for col in df.columns:
        if "date" in col.lower():
            date_col = col
            break
    
    if date_col:
        df[date_col] = pd.to_datetime(df[date_col], dayfirst=True, errors='coerce')
        df['Month'] = df[date_col].dt.strftime('%B')
        df.drop(columns=[date_col], inplace=True)
        cols = ['Month'] + [c for c in df.columns if c != 'Month']
        df = df[cols]

    # B. NAME CLEANING
    if 'state' in df.columns:
        df['state'] = df['state'].astype(str).str.strip().str.title()
    if 'district' in df.columns:
        df['district'] = df['district'].astype(str).str.strip().str.title()

    state_fixes = {
        '100000': None, 'Select': None,
        'Westbengal': 'West Bengal', 'West Bangal': 'West Bengal',
        'Orissa': 'Odisha', 'Pondicherry': 'Puducherry',
        'Dadra & Nagar Haveli': 'Dadra and Nagar Haveli and Daman and Diu',
        'Daman & Diu': 'Dadra and Nagar Haveli and Daman and Diu',
        'Jammu & Kashmir': 'Jammu and Kashmir',
        'Andaman & Nicobar Islands': 'Andaman and Nicobar Islands'
    }
    
    district_fixes = {
        'Namakkal *': 'Namakkal', 'Tuticorin': 'Thoothukkudi',
        'Kancheepuram': 'Kanchipuram', 'Viluppuram': 'Villupuram',
        'Thiruvallur': 'Tiruvallur', 'The Nilgiris': 'Nilgiris'
    }

    if 'state' in df.columns:
        df['state'] = df['state'].replace(state_fixes)
    if 'district' in df.columns:
        df['district'] = df['district'].replace(district_fixes)

    return df

# --- 3. THE PROCESSING LOOP (UPDATED) ---
for folder in input_folders:
    # 1. Define Input Path (Inside 'raw/')
    input_path = os.path.join(raw_base_folder, folder)
    
    # 2. Define Output Path (Inside 'Cleaned_Data/')
    save_folder = os.path.join(output_base_folder, folder)
    os.makedirs(save_folder, exist_ok=True)
    
    # 3. Search for CSVs in the RAW folder
    csv_files = glob.glob(os.path.join(input_path, "*.csv"))
    
    if not csv_files:
        print(f"No CSV files found in: {input_path}")
        continue
        
    print(f"Processing folder: {folder}...")

    for file_path in csv_files:
        try:
            # Use latin1 encoding to handle government data issues
            df = pd.read_csv(file_path, low_memory=False, encoding='latin1')
            
            df_clean = clean_dataset(df)
            
            filename = os.path.basename(file_path)
            save_path = os.path.join(save_folder, filename)
            df_clean.to_csv(save_path, index=False)
            
            print(f"   -> Processed: {filename}")
            
        except Exception as e:
            print(f"   Error with {filename}: {e}")

print("\nDONE. Files cleaned and saved to 'Cleaned_Data/'")