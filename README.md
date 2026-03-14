# Stockfish Fishtest Docker Logger

An efficient, Python-based multi-threaded logger specifically designed to extract, parse, and store real-time logs from **Stockfish Fishtest workers** running in Docker containers into a PostgreSQL database.

## Overview

Fishtest is the distributed testing framework used to improve the [Stockfish](https://stockfishchess.org/) chess engine. This tool monitors the worker logs to track game results, engine versions, and termination reasons (like mate, adjudication, or draw rules) for further analysis or monitoring dashboards.

## Features

* **Tailored for Stockfish:** Specifically handles the log output format of Fishtest workers.
* **Real-time Monitoring:** Automatically discovers and monitors all running containers with a specific prefix (e.g., `fishtest-worker`).
* **Intelligent Buffering:** Solves the issue of fragmented Docker log packets by buffering chunks and processing only complete lines.
* **Multi-threading:** Each worker container is monitored in its own isolated thread to ensure non-blocking performance.
* **Auto-Cleanup:** Automatically detects stopped containers and removes them from the monitoring set.

## Requirements

* Docker & Docker Compose
* PostgreSQL Database
* Python 3.9+
* Libraries: `psycopg`, `docker`

## Setup

1.  **Prepare the Database:**
    Create the following table in your PostgreSQL database:
    ```sql
    CREATE TABLE fishtest (
        id SERIAL PRIMARY KEY,
        time TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        container_name TEXT,
        log_game_id INTEGER,
        white_engine TEXT,
        black_engine TEXT,
        win TEXT,
        termination_reason TEXT
    );
    ```

2.  **Configuration:**
    The script uses environment variables for connectivity. Ensure these are set in your environment or Docker setup:
    * `DB_HOST`: Hostname of the Postgres DB
    * `DB_NAME`: Database name
    * `DB_USER`: Database user
    * `DB_PASS`: Password
    * `DB_TABLE`: Target table (Default: `fishtest`)

3.  **Run the Script:**
    Place the `logger.py` script in your directory and run it:
    ```bash
    python logger.py
    ```

## Technical Details

### Stream Buffering
Fishtest workers often output logs in rapid bursts. Docker often transmits these in small fragments (chunks). This logger uses a buffer to collect these fragments and only triggers the parsing logic once a newline character (`\n`) is detected. This ensures that every finished game is captured accurately and no data is lost due to split packets.

### Parsing Logic
The results are extracted using the following Regular Expression:

`Finished game (?P<log_id>\d+) \((?P<white>.*?) vs (?P<black>.*?)\): (?P<res>[\d/1-]+) \{(?P<reason>.*?)\}`

`Finished game 62 (Base-b3a810a1c4 vs New-9cf4e41d1b): 1/2-1/2 {Draw by 3-fold repetition} `

`Finished game 47 (New-9cf4e41d1b vs Base-b3a810a1c4): 1-0 {White wins by adjudication}`

`Finished game 63 (New-db0fea68e7 vs Base-b3a810a1c4): 1-0 {White mates}`

`Finished game 60 (Base-b3a810a1c4 vs New-db0fea68e7): 1/2-1/2 {Draw by insufficient mating material}`

`Finished game 46 (Base-b3a810a1c4 vs New-9cf4e41d1b): 1/2-1/2 {Draw by stalemate}`



