import os
import duckdb
import pandas as pd

DB_PATH = "data/spotify_warehouse.db"

def init_db():
    """Initializes the Star Schema tables if they don't exist."""
    #Create the data directory if it doesn't exist
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

    with duckdb.connect(DB_PATH) as con:
        # FACT TABLE: Just the event and the ID
        con.execute("""
            CREATE TABLE IF NOT EXISTS fact_listening_history (
                played_at VARCHAR PRIMARY KEY,
                track_id VARCHAR,
                duration_ms BIGINT
            )
        """)
        
        # DIMENSION TABLE: All the descriptive metadata
        con.execute("""
            CREATE TABLE IF NOT EXISTS dim_tracks (
                track_id VARCHAR PRIMARY KEY,
                track_name VARCHAR,
                artist_name VARCHAR,
                artist_id VARCHAR,
                album_name VARCHAR,
                artist_genres VARCHAR[], 
                popularity INTEGER
            )
        """)
        print("Star Schema initialized: fact_listening_history & dim_tracks.")

def load_facts(df: pd.DataFrame):
    """Loads validated play events into the fact table."""
    if df.empty:
        return

    with duckdb.connect(DB_PATH) as con:
        # Select only the columns needed for the skinny fact table
        fact_df = df[['played_at', 'track_id', 'duration_ms']]
        con.execute("""
            INSERT INTO fact_listening_history
            SELECT * FROM fact_df
            ON CONFLICT (played_at) DO NOTHING;
        """)
        count = con.sql("SELECT COUNT(*) FROM fact_listening_history").fetchone()[0]
        print(f"Fact table updated. Total plays stored: {count}")

def load_dimensions(dim_df: pd.DataFrame):
    """Loads new track metadata into the dimension table."""
    if dim_df.empty:
        return
        
    with duckdb.connect(DB_PATH) as con:
        con.execute("""
            INSERT INTO dim_tracks
            SELECT * FROM dim_df
            ON CONFLICT (track_id) DO NOTHING;
        """)
        count = con.sql("SELECT COUNT(*) FROM dim_tracks").fetchone()[0]
        print(f"Dimension table updated. Total unique tracks stored: {count}")

def get_uncached_track_ids(track_ids: list) -> list:
    if not track_ids:
        return []
        
    with duckdb.connect(DB_PATH) as con:
        # Create a temporary table of the new IDs to compare inside SQL
        temp_df = pd.DataFrame({'track_id': track_ids})
        
        # Use a LEFT JOIN to find which IDs are NOT in our dim_tracks table
        # This is MUCH faster for large datasets
        uncached = con.execute("""
            SELECT t.track_id 
            FROM temp_df t
            LEFT JOIN dim_tracks d ON t.track_id = d.track_id
            WHERE d.track_id IS NULL
        """).df()['track_id'].tolist()
        
    return list(set(uncached))