import json
import pandas as pd
import pandera.pandas as pa # <-- Updated to fix warning

# 1. Define the Data Contract (Schema) using the updated pa namespace
listening_schema = pa.DataFrameSchema({
    "played_at": pa.Column(pd.StringDtype(), pa.Check.str_matches(r"^\d{4}-\d{2}-\d{2}T.*Z$")), 
    "track_id": pa.Column(pd.StringDtype(), nullable=False),
    "track_name": pa.Column(pd.StringDtype(), nullable=False),
    "artist_name": pa.Column(pd.StringDtype(), nullable=False),
    "duration_ms": pa.Column(pd.Int64Dtype(), pa.Check.greater_than(0)) 
})

def parse_spotify_json(raw_data: dict) -> pd.DataFrame:
    """Extracts the exact fields we need, enforcing column structure even if empty."""
    parsed_records = []
    expected_columns = ["played_at", "track_id", "track_name", "artist_name", "duration_ms"]
    
    for item in raw_data.get("items", []):
        track = item.get("track")
        
        if not track:
            continue
            
        record = {
            "played_at": item.get("played_at"),
            "track_id": track.get("id"),
            "track_name": track.get("name"),
            "artist_name": track.get("artists")[0].get("name") if track.get("artists") else "Unknown",
            "duration_ms": track.get("duration_ms")
        }
        parsed_records.append(record)
        
    return pd.DataFrame(parsed_records, columns=expected_columns)

def validate_data(df: pd.DataFrame) -> pd.DataFrame:
    """Runs the DataFrame through the Pandera schema."""
    try:
        validated_df = listening_schema.validate(df)
        print(f"Data Contract Passed! {len(validated_df)} rows validated.")
        return validated_df
    except pa.errors.SchemaError as e:
        print("DATA VALIDATION FAILED")
        print(f"Error: {e}")
        raise

if __name__ == "__main__":
    print("Starting Validation Engine...")
    
    try:
        with open("data/raw_response.json", "r") as f:
            raw_data = json.load(f)
    except FileNotFoundError:
        raise FileNotFoundError("Could not find data/raw_response.json. Run extract.py first!")

    # 1. Parse into a flat DataFrame
    df = parse_spotify_json(raw_data)
    print(f"Parsed {len(df)} records into a DataFrame.")

    # 2. Validate against our schema
    clean_df = validate_data(df)
    
    # 3. Show a preview of our beautiful, clean data
    print("\nClean Data Preview:")
    
    if not clean_df.empty:
        #Use standard Pandas printing instead of Markdown
        print(clean_df.head(3))
    else:
        print("No new tracks to preview (DataFrame is empty but structurally sound!).")