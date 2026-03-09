import duckdb

import json

import os

import pandas as pd



DB_PATH = "data/spotify_warehouse.db"

OUTPUT_PATH = "data/stats.json"



def generate_stats():

    if not os.path.exists(DB_PATH):

        return



    with duckdb.connect(DB_PATH) as con:

        # Base filter for the last 7 days

        weekly_filter = "WHERE CAST(f.played_at AS TIMESTAMP) >= CURRENT_TIMESTAMP - INTERVAL '7 days'"



        # 1. WEEKLY TOP 5 ARTISTS

        top_artists = con.sql(f"""

            SELECT d.artist_name, COUNT(f.played_at) as plays

            FROM fact_listening_history f

            JOIN dim_tracks d ON f.track_id = d.track_id

            {weekly_filter}

            GROUP BY 1 ORDER BY 2 DESC LIMIT 5

        """).df().to_dict(orient="records")



        # 2. WEEKLY TOP 5 TRACKS

        top_tracks = con.sql(f"""

            SELECT d.track_name, d.artist_name, COUNT(f.played_at) as plays

            FROM fact_listening_history f

            JOIN dim_tracks d ON f.track_id = d.track_id

            {weekly_filter}

            GROUP BY 1, 2 ORDER BY 3 DESC LIMIT 5

        """).df().to_dict(orient="records")



        # 3. WEEKLY TOP 5 ALBUMS

        top_albums = con.sql(f"""

            SELECT d.album_name, d.artist_name, COUNT(f.played_at) as plays

            FROM fact_listening_history f

            JOIN dim_tracks d ON f.track_id = d.track_id

            {weekly_filter}

            GROUP BY 1, 2 ORDER BY 3 DESC LIMIT 5

        """).df().to_dict(orient="records")



        # 4. TOTAL LISTENING TIME (ALL TIME)

        total_ms = con.sql("SELECT SUM(duration_ms) FROM fact_listening_history").fetchone()[0] or 0

        hours = (total_ms // 3600000)

        minutes = (total_ms % 3600000) // 60000



        stats = {

            "last_updated": pd.Timestamp.now().isoformat(),

            "total_listening_time": f"{hours}h {minutes}m",

            "top_artists_weekly": top_artists,

            "top_tracks_weekly": top_tracks,

            "top_albums_weekly": top_albums

        }



        with open(OUTPUT_PATH, "w") as f:

            json.dump(stats, f, indent=4)

if __name__ == "__main__":
    print("Generating stats from the data warehouse...")
    generate_stats()
    print(f"Stats saved to {OUTPUT_PATH}")