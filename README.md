# 🎧 Automated Spotify ETL & Analytics Pipeline

A production-grade, serverless Data Engineering project that extracts personal listening history, transforms it into an optimized **Star Schema**, and delivers live analytics to a portfolio frontend.



## 🚀 The Mission
The goal of this project was to move beyond simple scripts and build a fully automated, self-healing data platform. It handles everything from OAuth2 token refreshes to cloud-state management with zero manual intervention.

## 🛠 Tech Stack
| Component | Technology | Role |
| :--- | :--- | :--- |
| **Language** | Python 3.11 | Core logic and data manipulation. |
| **Orchestration** | GitHub Actions | Serverless CI/CD and bi-daily cron scheduling. |
| **Database** | DuckDB | OLAP-optimized, in-process database for analytical queries. |
| **Storage** | GitHub Actions Cache | State management for persisting the `.db` warehouse. |
| **Deployment** | GitHub PAT (Cross-Repo) | Decoupled architecture pushing data to a Next.js portfolio. |

## 🏗 Data Architecture
This project implements a **Star Schema** to optimize query performance and ensure data integrity:

* **Fact Table:** `fact_listening_history` (Granular stream data, timestamps, and foreign keys).
* **Dimension Tables:** `dim_tracks` (Track metadata, artist genres, and popularity).



## 🧠 Engineering Challenges & Solutions

### Challenge 1: Overcoming the 50-Track API Limit
**Problem:** Spotify's `recently-played` endpoint is capped at 50 tracks. Daily polling resulted in "data gaps" during high-activity periods where more than 50 songs were played in 24 hours.
**Solution:** I increased polling frequency to a 12-hour interval (`cron: '34 8,20 * * *'`). To handle the resulting data overlap, I implemented an **idempotent loading strategy** using the `played_at` timestamp as a Primary Key, ensuring the database remains a "Single Source of Truth" without duplicates.

### Challenge 2: API Rate Limiting & Resource Management
**Problem:** Spotify’s Web API employs dynamic rate limiting. On high-activity days, repeatedly fetching artist/genre metadata for every track was inefficient and risked triggering 429 "Too Many Requests" errors.

**Solution:** Developed a two-tier caching system to minimize external calls:
1. **In-memory:** An `ARTIST_CACHE` handles duplicates within a single run.
2. **Database-level:** A "Pre-fetch Filter" compares incoming data against the `dim_tracks` table.
*Note: While `Get Several Tracks` is currently utilized for batch efficiency, it is noted as deprecated in the Spotify Web API reference; the architecture is designed for a modular transition to single-track lookups if the endpoint is retired.*

### Challenge 4: Future-Proofing against API Deprecations
**Problem:** Recent shifts in the Spotify Developer Roadmap have made specific endpoints, such as `Audio Features`, unstable or "not safe to depend on" for applications in Development Mode.
**Solution:** Built the schema to be **Metadata-Resilient**. I prioritized stable Dimension data (Genres, Popularity, Artist Metadata) over high-risk endpoints, ensuring the analytics engine remains functional regardless of specific attribute deprecations.

## 💡 Engineering Highlights
* **High-Frequency Ingestion:** effectively doubled data throughput by optimizing polling windows.
* **Efficient SQL Modeling:** Utilized DuckDB's `UNNEST` and CTEs to flatten nested JSON arrays into clean relational tables.
* **Decoupled CI/CD:** Built a cross-repo push mechanism using GitHub PATs to keep the data pipeline independent from the UI code.

## ⚙️ How It Works
1.  **Trigger:** GitHub Actions wakes up twice daily at off-peak hours to avoid runner congestion.
2.  **Extract:** Python fetches the Spotify `recently-played` endpoint using an automated OAuth2 refresh flow.
3.  **Transform:** Raw data is cleaned and deduplicated using Pandas and DuckDB.
4.  **Load:** Incremental data is loaded into the `spotify_warehouse.db` stored in the Action Cache.
5.  **Publish:** SQL analytics are exported to a lightweight `stats.json`.
6.  **Deploy:** The payload is pushed to the Next.js repo, triggering a fresh build on the live portfolio.

## 📂 Project Structure
```text
├── .github/workflows/  # CI/CD & Orchestration
├── src/
│   ├── extract.py      # API Interaction & In-memory Caching
│   ├── load.py         # Star Schema & Incremental Loading
│   ├── publish.py      # SQL Analytics (DuckDB)
│   ├── pipeline.py     # Execution Orchestrator
|   └── validate.py     # Data Checks
├── data/               # Persistent analytics (stats.json)
└── requirements.txt    # Dependency management