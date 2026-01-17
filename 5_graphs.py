import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import os

# --- 0. FOLDER SETUP ---
output_folder = "visuals_graphs"
if not os.path.exists(output_folder):
    os.makedirs(output_folder)
    print(f"Created folder: {output_folder}/")
else:
    print(f"Using existing folder: {output_folder}/")

# --- 1. LOAD & PREP DATA ---
print("Loading EMA Data...")

try:
    # A. Load EMA Gap Analysis (New File)
    df_data = pd.read_json("Cleaned_Data/statistical_gap_analysis.json", orient='records')
    
    # Ensure pincode is string
    df_data['pincode'] = df_data['pincode'].astype(str).str.strip()
    
    # B. ASSIGN SEVERITY (Since it wasn't in the raw JSON)
    # Logic: 3+ = Extreme, 2+ = Critical, 1+ = High, 0-1 = Moderate
    def get_severity(z):
        if z >= 3.0: return "Extreme"
        if z >= 2.0: return "Critical"
        if z >= 1.0: return "High"
        return "Moderate"
    
    df_data['severity'] = df_data['z_score'].apply(get_severity)

    # C. Load Master CSV for Geo-mapping
    df_geo = pd.read_csv("Cleaned_Data/pincode_master_clean.csv", dtype=str)
    df_geo.columns = df_geo.columns.str.lower().str.strip()
    df_geo['pincode'] = df_geo['pincode'].str.strip().str.split('.').str[0]

    # Rename 'statename' to 'state' if needed
    if 'statename' in df_geo.columns:
        df_geo.rename(columns={'statename': 'state'}, inplace=True)
    
    # Check for required columns
    if 'state' not in df_geo.columns or 'district' not in df_geo.columns:
        print("ERROR: Missing 'state' or 'district' columns in master CSV.")
        exit()

    # D. Merge
    df_merged = pd.merge(df_data, df_geo, on='pincode', how='inner')
    
    if df_merged.empty:
        print("Error: Merge resulted in 0 rows. Check Master CSV pincode formats.")
        exit()
        
    print(f"Successfully matched {len(df_merged)} records.")

except Exception as e:
    print(f"Error loading data: {e}")
    exit()

# Set visual style
sns.set_theme(style="whitegrid")
plt.rcParams['font.family'] = 'sans-serif'

# ==========================================
# PART A: CALCULATE "CRITICALITY INDEX (%)"
# ==========================================
print("Calculating Criticality Index...")

# Find the maximum Z-Score in the entire dataset (The "Worst Case")
max_z = df_merged['z_score'].max()

# Calculate Percentage relative to the worst case
# 100% = The highest EMA stress observed
df_merged['Criticality_Index'] = (df_merged['z_score'] / max_z) * 100


# ==========================================
# PART B: EXPORT TOP 200 CSV (Cleaned)
# ==========================================
print("Generating Top 200 CSV...")

# 1. Sort by Criticality Index Descending (Worst First)
top_200 = df_merged.sort_values(by='Criticality_Index', ascending=False).head(200).copy()

# 2. Round to 2 Decimals for clean reading
top_200['Criticality_Index'] = top_200['Criticality_Index'].round(2)

# 3. Select User-Friendly Columns 
# Note: 'EMA_i' is the internal calculated score, usually we hide it or show it as 'Gap Score'
csv_output = top_200[['pincode', 'district', 'state', 'severity', 'Criticality_Index']]

# 4. Save to Folder
csv_path = os.path.join(output_folder, 'Top_200_Critical_EMA_Pincodes.csv')
csv_output.to_csv(csv_path, index=False)
print(f"Saved Clean CSV: {csv_path}")


# ==========================================
# PART C: VISUALIZATIONS (Saved to Folder)
# ==========================================

# --- VISUAL 1: SEVERITY COUNT ---
print("Generating Visual 1 (Severity)...")
plt.figure(figsize=(10, 6))
order = ['Extreme', 'Critical', 'High', 'Moderate']
colors = {'Extreme': '#ff0033', 'Critical': '#ff6600', 'High': '#ffd700', 'Moderate': '#00ffff'}

existing_order = [x for x in order if x in df_merged['severity'].unique()]
ax = sns.countplot(x='severity', data=df_merged, order=existing_order, palette=colors)

for p in ax.patches:
    if p.get_height() > 0:
        ax.annotate(f'{int(p.get_height())}', (p.get_x() + p.get_width() / 2., p.get_height()),
                    ha='center', va='center', fontsize=12, color='black', xytext=(0, 5),
                    textcoords='offset points')

plt.title('Severity Distribution (EMA Weighted)', fontsize=16, fontweight='bold')
plt.xlabel('Severity Zone')
plt.ylabel('Number of Pincodes')
plt.tight_layout()
plt.savefig(os.path.join(output_folder, 'Visual_1_EMA_Severity.png'), dpi=300)

# --- VISUAL 2: TOP 10 STATES ---
print("Generating Visual 2 (States)...")
high_impact = df_merged[df_merged['severity'].isin(['Extreme', 'Critical'])]

if not high_impact.empty:
    plt.figure(figsize=(12, 8))
    state_counts = high_impact['state'].value_counts().head(10)
    sns.barplot(x=state_counts.values, y=state_counts.index, palette="Reds_r")
    
    plt.title('Top 10 States with Critical EMA Gaps', fontsize=16, fontweight='bold')
    plt.xlabel('Number of Critical Zones')
    plt.tight_layout()
    plt.savefig(os.path.join(output_folder, 'Visual_2_EMA_State_Impact.png'), dpi=300)

# --- VISUAL 3: TOP 15 DISTRICTS ---
print("Generating Visual 3 (Districts)...")

# Group by district
# IMPORTANT: Using 'EMA_i' instead of 'raw_load'
district_group = df_merged.groupby(['district', 'state']).agg({
    'EMA_i': 'sum',               # Sum of Exponential Moving Averages
    'Criticality_Index': 'mean',  # Average Severity
    'pincode': 'count'
}).reset_index()

# Rename for clarity
district_group.columns = ['District', 'State', 'Cumulative_EMA_Gap', 'Avg_Criticality', 'Critical_Pincodes_Count']

# Sort by the cumulative gap
top_districts = district_group.sort_values(by='Cumulative_EMA_Gap', ascending=False).head(15)

plt.figure(figsize=(12, 8))
sns.barplot(x='Cumulative_EMA_Gap', y='District', data=top_districts, palette="magma")
plt.title('Top 15 Districts with Highest EMA Gap Volume', fontsize=16, fontweight='bold')
plt.xlabel('Cumulative Weighted Demand Score (EMA)')
plt.ylabel('District')
plt.tight_layout()
plt.savefig(os.path.join(output_folder, 'Visual_3_EMA_Top_Districts.png'), dpi=300)

print(f"\n>>> SUCCESS! All files saved in '{output_folder}/'")