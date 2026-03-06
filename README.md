# 🎧 Automated Spotify ETL & Analytics Pipeline

A production-grade, serverless Data Engineering project that extracts personal listening history, transforms it into an optimized **Star Schema**, and delivers live analytics to a portfolio frontend.



## 🚀 The Mission
The goal of this project was to move beyond simple scripts and build a fully automated, self-healing data platform. It handles everything from OAuth2 token refreshes to cloud-state management with zero manual intervention.

## 🛠 Tech Stack
| Component | Technology | Role |
| :--- | :--- | :--- |
| **Language** | Python 3.11 | Core logic and data manipulation. |
| **Orchestration** | GitHub Actions | Serverless CI/CD, event-driven execution, and cron scheduling. |
| **Database** | DuckDB | OLAP-optimized, in-process database for analytical queries. |
| **Storage** | GitHub Actions Cache | State management for persisting the `.db` file across runs. |
| **Deployment** | GitHub PAT (Cross-Repo) | Decoupled architecture pushing data to a separate frontend repo. |

## 🏗 Data Architecture
This project implements a **Star Schema** to optimize query performance and ensure data integrity:

* **Fact Table:** `fact_listening_history` (Granular stream data, timestamps, and foreign keys).
* **Dimension Tables:** `dim_tracks` (Track metadata, artist genres, and popularity).



### 💡 Engineering Highlights
* **Self-Healing Infrastructure:** Implemented logic to dynamically generate directory structures on ephemeral cloud runners to prevent IO errors.
* **Robust SQL Modeling:** Utilized Common Table Expressions (CTEs) and DuckDB's `UNNEST` function to flatten nested JSON API responses into relational models.
* **Decoupled Architecture:** Built a cross-repo push mechanism using GitHub Personal Access Tokens (PAT). This allows the data pipeline to stay separate from the UI code, triggering a Vercel redeploy only when data updates.
* **State Management:** Leveraged GitHub Actions Cache to persist the DuckDB warehouse, allowing for cumulative data growth over time without an external managed database.

## ⚙️ How It Works
1.  **Trigger:** GitHub Actions wakes up daily via a `cron` schedule.
2.  **Extract:** Python fetches the Spotify `recently-played` endpoint using an OAuth2 refresh flow.
3.  **Transform:** Raw data is cleaned and deduplicated using Pandas and DuckDB.
4.  **Load:** Data is modeled into the Star Schema within the `spotify_warehouse.db`.
5.  **Publish:** SQL analytics are exported to a lightweight `stats.json`.
6.  **Deploy:** The payload is pushed to the Next.js portfolio repo, updating the live site.



## 📂 Project Structure
```text
├── .github/workflows/  # CI/CD & Orchestration
├── src/
│   ├── extract.py      # Spotify API interaction
│   ├── load.py         # Star Schema & DB initialization
│   ├── publish.py      # SQL analytics & JSON generation
│   └── pipeline.py     # Main execution orchestrator
├── data/               # Persistent analytics (stats.json)
└── requirements.txt    # Dependency management