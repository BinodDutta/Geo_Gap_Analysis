import pandas as pd

# 1. Load the RAW Pincode File

df = pd.read_csv("raw_data/pincode_india.csv", low_memory=False)

# 2. Define the Columns we actually need
# We drop 'officename', 'divisionname' etc. to make the file smaller and faster.
required_columns = ['pincode', 'district', 'statename', 'latitude', 'longitude']

# Check if columns exist (case-sensitive safety check)
# This handles "PinCode" vs "pincode" issues
df.columns = df.columns.str.lower().str.strip() # Normalize headers to lowercase
df = df[['pincode', 'district', 'statename', 'latitude', 'longitude']]

# 3. CLEANING LOGIC
print(f"Original Row Count: {len(df)}")

# A. Remove rows with Missing (NaN) Lat/Long
df = df.dropna(subset=['latitude', 'longitude'])

# B. Remove rows where Lat/Long is 0 (Common error in India datasets)
df = df[(df['latitude'] != 0) & (df['longitude'] != 0)]

# C. Remove Duplicate Pincodes
# A pincode like 110001 might have 10 Post Offices. We only need the location ONCE.
df = df.drop_duplicates(subset=['pincode'], keep='first')

print(f"Clean Row Count: {len(df)}")

# 4. DATA TYPE FIX
# Ensure Pincode is a string (so it doesn't lose leading zeros if any, though India pincodes are 6 digits)
df['pincode'] = df['pincode'].astype(int) 

# 5. SAVE THE PERFECT MASTER FILE
df.to_csv("Cleaned_Data/pincode_master_clean.csv", index=False)
print("Success! Created 'pincode_master_clean.csv'. Use this for the merger.")