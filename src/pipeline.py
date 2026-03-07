import os
import sys
import time  # <-- Added the time module
import pandas as pd
from extract import get_access_token, fetch_recently_played, fetch_track_metadata
from validate import parse_spotify_json, validate_data
from load import init_db, load_facts, load_dimensions, get_uncached_track_ids, DB_PATH
import duckdb

def get_latest_timestamp_ms() -> int | None:
    """Queries DuckDB for the most recent track to enable Incremental Extraction."""
    if not os.path.exists(DB_PATH):
        return None
        
    with duckdb.connect(DB_PATH) as con:
        try:
            # Note: We now query the fact_listening_history table!
            result = con.sql("SELECT MAX(played_at) FROM fact_listening_history").fetchone()[0]
            if result:
                dt = pd.to_datetime(result)
                return int(dt.timestamp() * 1000)
        except duckdb.CatalogException:
            return None
            
    return None

if __name__ == "__main__":
    print("Starting Optimized Spotify Star Schema Pipeline...")
    
    # STEP 1: Setup DB and get our "checkpoint"
    init_db()
    last_played_ms = get_latest_timestamp_ms()
    
    if last_played_ms:
        print(f"Incremental Run: Fetching tracks after UNIX {last_played_ms}")
    else:
        print("Initial Run: Fetching last 50 tracks")

    # STEP 2: Extract Recent Plays
    token = get_access_token()
    raw_data = fetch_recently_played(token, after_timestamp=last_played_ms)
    
    items = raw_data.get("items", [])
    print(f"API returned {len(items)} new plays.")

    if not items:
        print("No new tracks to process. Pipeline finished successfully.")
        sys.exit(0)

    # STEP 3: Validate Fact Data
    df_raw = parse_spotify_json(raw_data)
    df_clean = validate_data(df_raw)
    
    # Note: df_clean still has track_name and artist_name because of our old Pandera schema, 
    # but load_facts() is smart enough to only grab the 3 columns it needs for the Fact table!

    # STEP 4: Load Facts
    print("\nLoading Facts...")
    load_facts(df_clean)

    # STEP 5: Collect Track IDs & Check Cache
    all_track_ids = df_clean['track_id'].unique().tolist()
    uncached_ids = get_uncached_track_ids(all_track_ids)

    # STEP 6: Fetch Metadata for Uncached Tracks
    if uncached_ids:
        print(f"\nFound {len(uncached_ids)} uncached tracks. Fetching deep metadata...")
        print(uncached_ids)
        dimension_records = []
        for tid in uncached_ids:
            meta = fetch_track_metadata(token, tid)
            if meta:
                dimension_records.append(meta)
            
            # <-- ADDED DELAY: 1.5 seconds of breathing room to prevent 429 errors
            time.sleep(1.5)
                
        # STEP 7 & 8: Build Dimension DataFrame & Load
        if dimension_records:
            df_dim = pd.DataFrame(dimension_records)
            print("Loading Dimensions...")
            load_dimensions(df_dim)
    else:
        print("\nAll tracks already have metadata cached in dim_tracks.")

    print("\nPipeline complete!")