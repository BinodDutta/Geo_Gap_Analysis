Here is a professional `README.md` based strictly on the code provided.

### **Important Analysis of Your Code's Logic**

Before the README, here is the breakdown of the exact Math and Logic currently implemented in your uploaded files:

* **The Logic:** You are using a **Weighted Demand Aggregation** model. You prioritize specific transaction types (Biometrics > Demographics > Enrolment) because they require more resources (time/hardware).
* **The Math:** You are using **Z-Score Normalization** (Standard Deviation). You calculate a `raw_load` for every pincode and then compare it to the national average.
* *Formula:* 
* If a pincode's Z-Score is **> 3.0**, it is flagged as an "Extreme" anomaly (3 Standard Deviations above the mean).


* **The "AI" Component:** You are using **Unsupervised Anomaly Detection** via `scikit-learn`'s `StandardScaler`. This automatically learns the distribution of your data to identify outliers without needing labeled training data.

---

#  Digital Gap Analysis: Aadhaar Service Coverage

### A Geospatial Intelligence System to identify underserved regions using Statistical Anomaly Detection.

---

##  Overview

This project addresses the challenge of identifying gaps in Aadhaar service infrastructure. Instead of simply counting centers, this system analyzes **transactional stress** (Enrolments, Updates, Biometrics) to find regions where the demand significantly outstrips the statistical norm.

It uses **Weighted Aggregation** and **Z-Score Normalization** to flag high-stress pincodes as "Critical" or "Extreme" zones, visualizing them on an interactive map for actionable decision-making.

---

##  Logic & Methodology

### 1. Robust Data Extraction (Regex)

* **Problem:** Raw government datasets often have inconsistent column headers.
* **Solution:** The system uses **Regular Expressions (`\d{6}`)** to automatically scan every CSV file, identifying any column that contains 6-digit Pincodes with >10% density. This allows it to ingest noisy data without manual column mapping.

### 2. Weighted Demand Calculation

Not all transactions are equal. We calculate a `raw_load` score for every pincode using weighted importance:


* *Reasoning:* Biometric updates require scanners and more time, so they are weighted heavily () compared to simple enrolments ().

### 3. Statistical Anomaly Detection (The AI)

We use `scikit-learn`'s **StandardScaler** to normalize the `raw_load` distribution. This converts raw numbers into **Z-Scores** (Standard Deviations from the mean).

* **Extreme Zone:** Z-Score  (Statistically rare outliers).
* **Critical Zone:** Z-Score .
* **High Zone:** Z-Score .

### 4. Criticality Indexing

For the final reports, we calculate a relative percentage index:



This ranks the "Worst" pincode as 100%, providing a linear scale for prioritization.

---

##  Tech Stack

* **Core Logic:** Python 3.10+
* **Data Processing:** `Pandas`, `NumPy`
* **Machine Learning:** `Scikit-learn` (StandardScaler)
* **Visualization:** `Folium` (Maps), `Seaborn` (Charts), `Matplotlib`
* **Geospatial:** `Shapely` (Boundary validation), `Branca`

---

##  Project Structure

```text
Digital_Gap_Analysis/
│
├── raw_data/                 # Input CSVs (Biometric/Demographic/Enrolment)
│
├── Cleaned_Data/             # Processed datasets (Auto-generated)
│   ├── statistical_gap_analysis.json  # The calculated Z-Scores
│   └── pincode_master_clean.csv       # Standardized Geolocation data
│
├── visuals_graphs/           # Output Reports
│   ├── India_Map_Service_Coverage.html # 📍 Interactive Map
│   └── Top_200_Critical_Pincodes.csv   # 📄 Priority List
│
└── scripts/
    ├── 0_install_deps.py     # Setup Script
    ├── 1_data_parsing.py     # Data standardization
    ├── 2_pincode_clean.py    # Geo-tagging cleaner
    ├── 3_calc_severity.py    # MATH ENGINE (Z-Score & Weights)
    ├── 4_logic_plotting.py   # Map Generator
    └── 5_graphs.py           # Statistical Reporting

```

---

##  How to Run

### Step 1: Setup

Run the auto-installer to configure your environment.

```bash
python 0_install_deps.py

```

*(Installs pandas, sklearn, folium, etc. from requirements.txt)*.

### Step 2: Data Cleaning

Standardize the raw transaction logs and state names.

```bash
python 1_data_parsing.py

```

*(Handles date formats, standardizes 'Orissa' -> 'Odisha', etc.)*.

### Step 3: Geo-Tagging Prep

Clean the Pincode directory to ensure accurate plotting.

```bash
python 2_pincode_clean.py

```

*(Removes duplicates and invalid lat/long coordinates)*.

### Step 4: The Math Engine (Crucial)

Calculate the Z-Scores and Severity levels.

```bash
python 3_calc_severity.py

```

*Output:* `Cleaned_Data/statistical_gap_analysis.json`

### Step 5: Visualization

Generate the Interactive Map and Statistical Reports.

```bash
python 4_logic_plotting_form.py
python 5_graphs.py

```

*Output:* Check the `visuals_graphs/` folder for the HTML map and the Top 200 CSV.

---

##  Map Legend

| Color | Severity | Definition | Statistical Logic |
| --- | --- | --- | --- |
| 🔴 **Red** | **Extreme** | Highest Priority | Z-Score  |
| 🟠 **Orange** | **Critical** | High Stress | Z-Score  |
| 🟡 **Yellow** | **High** | Above Average | Z-Score  |
| 🔵 **Cyan** | **Moderate** | Normal | Z-Score  |

---

### ⚠️ Limitations

* **Geo-Filtering:** Points falling outside the official India GeoJSON boundary are automatically dropped to maintain map integrity.
* **Data Matching:** If a pincode exists in transaction logs but not in the Master Geo-CSV, it is excluded from the map.