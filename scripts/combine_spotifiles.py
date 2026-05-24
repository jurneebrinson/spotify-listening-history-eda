import pandas as pd
import glob
import json

# Path to your folder (change this to match where your files are)
path = "data/raw"

# Get all JSON files
files = glob.glob(f"{path}/*.json")

# Load and combine them
dfs = []

for file in files:
    with open(file, "r", encoding="utf-8") as f:
        data = json.load(f)
        df = pd.DataFrame(data)
        dfs.append(df)

# Combine all into one dataframe
combined_streaming_history = pd.concat(dfs, ignore_index=True)

# Optional: convert time column to datetime
if 'ts' in combined_streaming_history.columns:
    combined_streaming_history['ts'] = pd.to_datetime(combined_streaming_history['ts'])

# Save to CSV
combined_streaming_history.to_csv(f"{path}/Spotify_Streaming_History_Combined.csv", index=False)

print("✅ Combined CSV saved successfully!")
print(f"Total rows: {len(combined_streaming_history)}")
