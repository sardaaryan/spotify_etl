import duckdb
import json
import os
import pandas as pd

DB_PATH = "data/spotify_warehouse.db"
OUTPUT_PATH = "data/stats.json"

def generate_stats():
    """Queries the Star Schema and exports metrics to a JSON file for front-end consumption."""
    if not os.path.exists(DB_PATH):
        print("🛑 Database not found. Run the pipeline first.")
        return

    with duckdb.connect(DB_PATH) as con:
        # 1. TOP 5 ARTISTS (Joining Fact and Dimension tables)
        top_artists_df = con.sql("""
            SELECT d.artist_name, COUNT(f.played_at) as plays
            FROM fact_listening_history f
            JOIN dim_tracks d ON f.track_id = d.track_id
            GROUP BY 1
            ORDER BY 2 DESC
            LIMIT 5
        """).df()

        # 2. TOTAL LISTENING TIME (Converting milliseconds to Hours/Minutes)
        total_ms_df = con.sql("""
            SELECT SUM(duration_ms) as total_ms
            FROM fact_listening_history
        """).df()
        
        total_ms = int(total_ms_df['total_ms'][0]) if not pd.isna(total_ms_df['total_ms'][0]) else 0
        total_minutes = total_ms // 60000
        hours = total_minutes // 60
        minutes = total_minutes % 60
        listening_time = f"{hours}h {minutes}m"

        # 3. TOP GENRES (Using UNNEST to explode the array column)
        top_genres_df = con.sql("""
            SELECT unnest(d.artist_genres) as genre, COUNT(f.played_at) as plays
            FROM fact_listening_history f
            JOIN dim_tracks d ON f.track_id = d.track_id
            GROUP BY 1
            ORDER BY 2 DESC
            LIMIT 5
        """).df()

        # 4. COMPILE THE JSON PAYLOAD
        # orient="records" turns a Pandas DataFrame into a list of dictionaries (perfect for JSON)
        stats = {
            "last_updated": pd.Timestamp.now().isoformat(),
            "total_listening_time": listening_time,
            "top_artists": top_artists_df.to_dict(orient="records"),
            "top_genres": top_genres_df.to_dict(orient="records")
        }

        # 5. EXPORT TO STATIC FILE
        with open(OUTPUT_PATH, "w") as f:
            json.dump(stats, f, indent=4)
        
        print(f"✅ Analytics successfully published to {OUTPUT_PATH}!")
        print("\n--- Payload Preview ---")
        print(json.dumps(stats, indent=4))

if __name__ == "__main__":
    print("📊 Generating Portfolio Analytics...")
    generate_stats()