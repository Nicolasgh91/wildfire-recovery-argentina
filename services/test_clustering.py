import pandas as pd
from fire_processor import cluster_fire_detections

# 📥 Load your local NASA CSV
DATA_PATH = "./raw_data/nasa_detections_2015_2026.csv"
print("\n")
print(f"--- 🚀 Starting Wildfire Recovery Processor ---\n")
print(f"Reading file: {DATA_PATH}")

df = pd.read_csv(DATA_PATH)
initial_count = len(df)
print(f"📊 Initial detections loaded: {initial_count}")

# ⚙️ Run the clustering logic
print("\n--- 🛠 Processing Filters ---")
result_df = cluster_fire_detections(df)

# 🏁 Final Results
print("\n--- ✅ Processing Complete ---")
if not result_df.empty:
    final_count = len(result_df)
    reduction = ((initial_count - final_count) / initial_count) * 100
    
    print(f"🔥 Consolidated Unique Events: {final_count}")
    print(f"📉 Data Reduction Rate: {reduction:.2f}%")
    
    # Show significance breakdown
    significant_count = result_df['is_significant'].sum()
    print(f"🌟 Significant fires (High Priority): {significant_count}")
    print(f"⚠️ Minor events filtered: {final_count - significant_count}")

    # Preview top events by energy
    print("\n--- 🔝 Top 50 Most Energetic Events ---")
    top_fires = result_df.sort_values(by='sum_frp', ascending=False).head(50)
    print(top_fires[['start_date', 'total_detections', 'sum_frp', 'avg_confidence']])
else:
    print("❌ No events survived the filtering process.")