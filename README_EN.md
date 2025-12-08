# Project AEGIS: Hybrid Algorithmic Trading System (v2.2)

> **[Leer en Español](README.md)**

**Project AEGIS** is a low-resource, high-autonomy trading system designed for the Raspberry Pi 4. It implements a "Pilot vs. Strategist" architecture where a deterministic trading bot (The Pilot) is guided by an LLM-powered risk manager (The Strategist), and now features a self-evolving strategy engine ("Operation EVO").

## 1. Architecture Overview

### Current Architecture (v2.2)
The current system operates with a single strategist agent and an evolution engine.

```mermaid
graph TD
    subgraph Hardware [Raspberry Pi 4 8GB RAM]
        subgraph Docker_Network [Internal Network: trading_net]
            Pilot[Freqtrade - The Pilot] -- "Executes Trades" --> Exchange((Exchange))
            Pilot -- "API" --> Bridge
            Bridge[MCP Wrapper - Kukapay Freqtrade MCP] -- "Exposes Tools (HTTP)" --> Strategist
            Strategist[AEGIS Brain - The Strategist] -- "MCP Client" --> Bridge
            Strategist -- "Context/Evolution" --> Gemini((Google Gemini))
            Strategist -- "Store/Recall" --> Memory[SQLite BankMemory]
            Strategist -- "Mutates" --> PilotStrategy[Strategy File]
        end
    end
```

### Future Architecture (Beast Mode - In Development)
The system is evolving into a Multi-Agent decision engine ("The War Room") with external data ingestion.

```mermaid
graph TD
    subgraph External_Data [The Eyes]
        Whale[Whale Watcher] -- "On-Chain Flows" --> WarRoom
        Social[Sentiment Sniper] -- "Hype Score" --> WarRoom
        Market[Market Data] -- "Price/Indicators" --> WarRoom
    end

    subgraph The_War_Room [The Brain]
        direction TB
        Bull[Agent Alpha: The Bull]
        Bear[Agent Beta: The Bear]
        Risk[Agent Gamma: Risk Judge]
        
        Whale & Social & Market --> Bull & Bear & Risk
        
        Bull -- "Vote" --> Voting[Weighted Voting Mechanism]
        Bear -- "Vote" --> Voting
        Risk -- "Vote" --> Voting
        
        Voting -- "Final Verdict" --> Commander[Supreme Commander]
    end

    subgraph Execution [The Muscle]
        Commander -- "Long/Short/Hold" --> Pilot[Freqtrade - Futures]
        Commander -- "Emergency Hedge" --> Shield[Delta Neutral Shield]
    end
```

### Components
1.  **The Pilot (Freqtrade):** Runs the `BBRSI_Optimized` strategy. It handles the minute-by-minute execution of trades.
2.  **The Bridge (MCP Wrapper):** A containerized FastAPI application acting as an MCP Server. It wraps [kukapay/freqtrade-mcp](https://github.com/kukapay/freqtrade-mcp) and exposes Freqtrade's API as Model Context Protocol (MCP) tools over HTTP.
3.  **The Strategist (AEGIS Brain):** A Python application acting as an **MCP Client**. It periodically fetches market context via the Bridge, consults Google Gemini for a risk assessment, and stores decisions in a local SQLite database.
4.  **Operation EVO (Evolution Engine):** A module within the Strategist that autonomously analyzes, mutates, and improves the trading strategy.

### New Feature: Operation EVO (Self-Evolving Strategy)
The system now includes an autonomous evolution cycle that runs weekly:
1.  **Analyze:** Queries the Freqtrade database to identify performance weaknesses (e.g., low win rate, high drawdown).
2.  **Mutate:** Uses Google Gemini to generate a *new* candidate strategy code (`BBRSI_Candidate.py`) designed to fix the identified weaknesses.
3.  **Backtest:** Uses the Docker SDK to trigger a backtest of the candidate strategy within the Freqtrade container.
4.  **Deploy:** (Safety Mode) Compares the candidate's performance against the current strategy. *Currently in safety mode: logs results but does not auto-swap.*

### Feature: Closed-Loop Memory Reinforcement
The Strategist possesses a "BankMemory" that allows it to learn from past decisions:
-   **Market Snapshots:** Before every decision, the context and the AI's reasoning are saved.
-   **Reconciliation:** The system periodically checks for closed trades and links them back to the original prediction.
-   **RAG (Retrieval-Augmented Generation):** When making a new decision, the Brain retrieves similar past scenarios and sees whether its past advice led to a Profit or Loss.

## 2. Hardware Setup (Raspberry Pi 4)

### Prerequisites
- Raspberry Pi 4 (4GB or 8GB recommended)
- SSD connected via USB 3.0 (MicroSD cards are not recommended for DB operations)
- Raspberry Pi OS (64-bit)

### Optimization Steps
1.  **Enable ZRAM:** To optimize memory usage on the Pi.
    ```bash
    sudo apt install zram-tools
    echo "PERCENT=50" | sudo tee -a /etc/default/zramswap
    sudo service zramswap reload
    ```
2.  **Install Docker & Docker Compose:**
    ```bash
    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh get-docker.sh
    sudo usermod -aG docker $USER
    sudo apt install -y docker-compose-plugin
    ```

## 3. Deployment

### Option A: Automated Setup (Recommended for Pi)
We provide a script to automate the installation of Docker, ZRAM, and directory setup.

1.  **Clone and Setup:**
    ```bash
    git clone <repo_url> project_aegis
    cd project_aegis
    chmod +x scripts/setup_pi.sh
    sudo ./scripts/setup_pi.sh
    ```
    *Reboot your Pi after setup.*

2.  **Configuration:**
    - Copy `.env.example` to `.env` and fill in your API keys.
    - Review `aegis_brain/config.yaml` to tune trading thresholds and weights.

3.  **Launch:**
    ```bash
    docker compose up -d
    ```

4.  **Updates:**
    To pull the latest code and restart:
    ```bash
    chmod +x scripts/update.sh
    ./scripts/update.sh
    ```

### Option B: Manual Setup
Follow the "Prerequisites" section above, then run `docker compose up -d`.

## 4. Testing & Verification

To verify the system logic (unit tests):
```bash
# Install dependencies
pip install -r aegis_brain/requirements.txt

# Run tests
python3 -m unittest discover aegis_brain/tests
```

## 5. Project Structure

```
project_aegis/
├── aegis_brain/          # The Strategist (MCP Client + LLM Logic)
│   ├── brain.py          # Main logic loop
│   ├── config.yaml       # Configuration (Thresholds, Schedule)
│   ├── memory_manager.py # SQLite Database Manager
│   ├── strategy_evolver.py # Operation EVO (Evolution Engine)
│   ├── tests/            # Unit Tests
│   ├── Dockerfile        # Container definition
│   └── requirements.txt  # Python dependencies
├── freqtrade/            # The Pilot (Trading Bot)
│   └── user_data/
│       └── strategies/
│           └── BBRSI_Optimized.py # Custom Strategy
├── mcp_wrapper/          # The Bridge (Kukapay Integration)
│   ├── main.py           # FastAPI MCP Server
│   └── Dockerfile        # Clones and builds kukapay/freqtrade-mcp
├── scripts/              # Maintenance scripts
│   ├── setup_pi.sh       # Automated setup script
│   └── update.sh         # Update script
├── docker-compose.yml    # Orchestration
├── .env.example          # Config template
└── .gitignore            # Git configuration
```

## 6. Security Notes
- **Network:** All containers communicate via an internal bridge network (`trading_net`). Only ports 8080 (Freqtrade UI) and 8000 (MCP Server) are exposed to the host.
- **Logs:** Docker logging is limited to 10MB per container to prevent SSD wear.
- **Secrets:** Never commit `.env` or `user_data/config.json` to version control.

---
*Generated by Antigravity for Project AEGIS*
