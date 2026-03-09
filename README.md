# 🎧 Automated Spotify ETL & Analytics Pipeline (Weekly Edition)

A production-grade, serverless Data Engineering project that extracts personal listening history, transforms it into an optimized **Star Schema**, and delivers fresh weekly analytics to a portfolio frontend.

## 🚀 The Mission
The goal of this project is to provide a rolling weekly snapshot of listening habits. It handles everything from OAuth2 token refreshes to **automated weekly state resets** using GitHub Actions cache rotation, ensuring the data remains relevant and the system remains self-healing.

## 🛠 Tech Stack
| Component | Technology | Role |
| :--- | :--- | :--- |
| **Language** | Python 3.11 | Core ETL logic and data manipulation. |
| **Orchestration** | GitHub Actions | Serverless cron scheduling and rotating cache management. |
| **Database** | DuckDB | OLAP-optimized, in-process database for windowed SQL queries. |
| **Validation** | Pandera | Strict data contract enforcement before warehouse ingestion. |
| **Deployment** | GitHub Actions | Cross-repo push mechanism delivering `stats.json` to the frontend. |

## 🏗 Data Architecture
The project utilizes a **Star Schema** to decouple granular event data from track metadata. 

* **Fact Table (`fact_listening_history`):** Stores every "play" event with a unique timestamp (`played_at`), track ID, and duration.
* **Dimension Table (`dim_tracks`):** A cached look-up table for track names, artist names, album names, and popularity. 
    * *Note: Genre tracking was deprecated in v2.0 due to API inconsistency.*



## ⚙️ How It Works

1.  **Trigger:** GitHub Actions runs twice daily.
2.  **Weekly Rotation:** The pipeline uses a rotating cache key based on the current ISO week. Every Monday, the cache resets, providing a clean slate for the new week's analytics.
3.  **Incremental Extract:** Python fetches the Spotify `recently-played` endpoint. It checks the local DuckDB instance for the latest `played_at` timestamp to avoid duplicate API calls.
4.  **Transform & Validate:** Raw JSON is flattened and validated against a Pandera schema to ensure no null IDs or malformed timestamps enter the system.
5.  **Load:** New events are inserted into the Fact table; metadata for new tracks is fetched once and cached in the Dimension table.
6.  **Publish:** SQL analytics generate a `stats.json` payload containing:
    * **Top 5 Artists** (Weekly)
    * **Top 5 Tracks** (Weekly)
    * **Top 5 Albums** (Weekly)
    * **Total Listening Time** (Current Week)



## 💡 Engineering Highlights

* **Rotating State Management:** Implemented dynamic GitHub Action cache keys (`duckdb-v2-${{ year }}-${{ week }}`) to automate schema migrations and weekly resets without manual intervention.
* **Rate Limit Mitigation:** Integrated `tenacity` for exponential backoff and a 1.5s "breathing room" delay between metadata requests to respect Spotify's API limits.
* **SQL Windowing:** Utilized DuckDB's interval arithmetic (`INTERVAL '7 days'`) to ensure analytics are strictly bound to the rolling week even if the cache persists.
* **Idempotency:** Designed the `load.py` module with `ON CONFLICT DO NOTHING` logic to ensure that overlapping ETL runs never result in duplicate data.

## 📂 Project Structure
```text
├── .github/workflows/  # CI/CD & Weekly Cache Rotation
├── src/
│   ├── extract.py      # OAuth2 Flow & Metadata Extraction
│   ├── load.py         # Star Schema Initialization & Upserts
│   ├── publish.py      # Weekly SQL Analytics Logic
│   ├── pipeline.py     # ETL Orchestrator
│   └── validate.py     # Pandera Data Contract Validation
├── data/               
│   ├── stats.json      # Final analytics payload
│   └── spotify_warehouse.db # DuckDB Local Warehouse (Cached)
└── requirements.txt    # Project dependencies