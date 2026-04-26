# BESS Grid Manager

A battery energy storage system monitoring and AI analysis platform built with FastAPI, SQLAlchemy, and Mistral via Ollama. The application exposes a REST API for querying BESS fleet data and accepts natural language questions about battery status, which are answered by a locally-running LLM with live access to the database.

---

## Table of Contents

1. [Project Overview](#project-overview)
2. [Architecture](#architecture)
3. [Data Models](#data-models)
4. [API Endpoints](#api-endpoints)
5. [Setting Up the Virtual Environment](#setting-up-the-virtual-environment)
6. [Connecting to Ollama and Mistral](#connecting-to-ollama-and-mistral)
7. [Running the Application](#running-the-application)
8. [Daily Development Workflow](#daily-development-workflow)
9. [Key Dependencies](#key-dependencies)

---

## Project Overview

BESS Grid Manager provides:

- A **REST API** for managing and querying battery asset data across a grid-scale fleet
- A **SQLite database** (`bess.db`) seeded with realistic data from real manufacturers (Tesla, Fluence, Sungrow, CATL, BYD, and others) across 31 batteries
- A **natural language query interface** powered by Mistral (via Ollama) using single-pass context injection — battery data is injected directly into the system prompt, and Mistral narrates the pre-computed results
- **RTE API integration** for live French grid signal data (Actual Generation and Balancing Energy endpoints)

---

## Architecture

```mermaid
graph TB
    Client["Client — Browser or API consumer"]

    subgraph App ["FastAPI Application"]
        API["REST Endpoints\nmain.py"]
        LLM["LLM Service\nllm_service.py"]
        DB["Database Layer\ndatabase.py · models.py"]
    end

    subgraph AI ["Local AI — Ollama"]
        Ollama["Ollama Server\nlocalhost:11434"]
        Mistral["mistral:7b-instruct"]
        Ollama --> Mistral
    end

    subgraph Data ["Persistence"]
        SQLite[("bess.db\nSQLite")]
    end

    subgraph External ["External APIs"]
        RTE["RTE API\nActual Generation\nBalancing Energy"]
    end

    Client -->|HTTP| API
    API --> LLM
    API --> DB
    LLM -->|Battery context injected into system prompt| Ollama
    DB -->|SQLAlchemy ORM| SQLite
    App -->|OAuth2 + REST| RTE
```

### How the LLM integration works

The application uses **single-pass context injection** rather than tool calling. When a natural language question arrives:

1. Battery data is queried from the database using SQLAlchemy
2. The results are serialised and injected directly into the Mistral system prompt
3. Mistral receives the question alongside the pre-computed data and narrates the answer
4. The response streams back to the client

This approach is simpler, faster, and more reliable than two-pass tool calling — Mistral never performs arithmetic on production data, it only narrates results that have already been computed by Python.

```mermaid
sequenceDiagram
    participant C as Client
    participant A as FastAPI
    participant DB as SQLite (bess.db)
    participant O as Ollama (Mistral)

    C->>A: POST /llm/ask  {"question": "..."}
    A->>DB: Query battery data (SQLAlchemy)
    DB-->>A: Pre-computed results
    A->>O: System prompt with injected data + question
    O-->>A: Streamed token response
    A-->>C: StreamingResponse
```

---

## Data Models

Five SQLAlchemy ORM models backed by SQLite:

```mermaid
erDiagram
    BATTERY {
        int id PK
        string name
        string manufacturer
        float capacity_kwh
        float max_charge_rate_kw
        bool is_active
    }

    STATE_OF_CHARGE {
        int id PK
        int battery_id FK
        float soc_pct
        datetime timestamp
    }

    BATTERY_TELEMETRY {
        int id PK
        int battery_id FK
        float voltage_v
        float current_a
        float temperature_c
        datetime timestamp
    }

    DISPATCH_COMMAND {
        int id PK
        int battery_id FK
        string command_type
        float power_kw
        datetime issued_at
    }

    GRID_SIGNAL {
        int id PK
        float total_generation_mw
        float renewable_mw
        float renewable_pct
        float imbalance_mw
        string imbalance_trend
        float fcr_activated_mw
        float calculated_frequency_hz
        datetime timestamp
    }

    BATTERY ||--o{ STATE_OF_CHARGE : "has"
    BATTERY ||--o{ BATTERY_TELEMETRY : "has"
    BATTERY ||--o{ DISPATCH_COMMAND : "receives"
```

> `GridSignal` is a standalone table — it records grid-level data independent of individual batteries. The `calculated_frequency_hz` column name is intentional: it signals that this value is derived from grid measurements, not directly measured.

---

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/` | Returns API name and status |
| `GET` | `/health` | Health check |
| `GET` | `/batteries` | All battery records |
| `POST` | `/llm/ask` | Natural language question — returns a streamed Mistral answer |

Interactive API docs are available at `http://127.0.0.1:8000/docs` when the server is running.

---

## Setting Up the Virtual Environment

The virtual environment is already created in the project root (`venv/`). You do not need to recreate it.

### Activate the virtual environment

```bash
# From the project root
source venv/bin/activate
```

Your terminal prompt will change to show `(venv)` when the environment is active.

### Install or update dependencies

```bash
pip install -r requirements.txt
```

### Key packages

| Package | Purpose |
|---|---|
| `fastapi` | Web framework |
| `uvicorn` | ASGI server |
| `sqlalchemy` | ORM — all five models |
| `ollama` | Python client for Ollama |
| `requests` | HTTP calls to RTE API |
| `python-dotenv` | Load credentials from `.env` |

### Deactivate when done

```bash
deactivate
```

---

## Connecting to Ollama and a Specific LLM

### 1. Install Ollama

If Ollama is not yet installed on your machine:

```bash
curl -fsSL https://ollama.com/install.sh | sh
```

Or download from [ollama.com](https://ollama.com) for macOS or Windows.

### 2. Pull the required model

This project uses `mistral:7b-instruct`. Pull it before running the app for the first time:

```bash
ollama pull mistral:7b-instruct
```

> **Important:** Use `mistral:7b-instruct` — not `mistral:7b-instruct-q8_0`. The `q8_0` quantisation variant does not support tool calling and returns HTTP 400 errors when invoked.

### 3. Start the Ollama server

Ollama must be running in a **separate terminal** before starting the FastAPI app:

```bash
ollama serve
```

Ollama listens on `http://localhost:11434` by default. You can verify it is running:

```bash
curl http://localhost:11434
# Expected: "Ollama is running"
```

### 4. Verify the model is available

```bash
ollama list
```

You should see `mistral:7b-instruct` in the output. If not, run `ollama pull mistral:7b-instruct` again.

### Switching to a different model

To use a different model, pull it first:

```bash
ollama pull llama3:8b
```

Then update the model name in `llm_service.py`:

```python
# Change this line
model = "mistral:7b-instruct"

# To your chosen model
model = "llama3:8b"
```

Restart the FastAPI server after changing the model.

### Performance note

On CPU-only hardware (no GPU), expect approximately 60–75 seconds time-to-first-token for a warm Mistral model. Subsequent requests are faster due to model caching. When the RTX 3090 home server is online, inference time is expected to drop below 10 seconds.

---

## Running the Application

### Prerequisites checklist

- [ ] Virtual environment activated (`source venv/bin/activate`)
- [ ] Ollama server running in a separate terminal (`ollama serve`)
- [ ] `mistral:7b-instruct` model pulled (`ollama list`)
- [ ] `.env` file present with RTE API credentials (required for grid signal fetching)

### Start the FastAPI server

```bash
uvicorn main:app --reload
```

The `--reload` flag enables hot-reloading — the server restarts automatically when you save changes to any Python file.

### First run

On first run, SQLAlchemy creates `bess.db` automatically in the project root. To populate it with realistic seed data:

```bash
python seed_batteries.py
```

---

## Daily Development Workflow

```mermaid
flowchart LR
    A["Activate venv\nsource venv/bin/activate"] --> B["Start Ollama\nollama serve\n(separate terminal)"]
    B --> C["Start FastAPI\nuvicorn main:app --reload"]
    C --> D["Open Swagger UI\nlocalhost:8000/docs"]
```

---

## Key Dependencies

See `requirements.txt` for pinned versions. Core packages:

```
fastapi
uvicorn
sqlalchemy
ollama
requests
python-dotenv
```

### Environment variables

Credentials are stored in `.env` in the project root (excluded from git). Required for RTE API access:

```
RTE_CLIENT_ID=your_client_id
RTE_CLIENT_SECRET=your_client_secret
```

---

*BESS Grid Manager · FastAPI · SQLAlchemy · SQLite · Mistral · Ollama · RTE API · Python*
