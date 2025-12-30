# Project AEGIS: Neuro-Genetic Hybrid System (v3.0)

> **[Leer en Español](README.md)**

**Project AEGIS** is an advanced trading system designed for low-resource hardware (e.g., Raspberry Pi 4). Evolving beyond simple generative AI, AEGIS v3.0 implements a **Neuro-Genetic Architecture** that separates qualitative creativity from quantitative optimization.

## 1. Architecture Overview (v3.0)

### The Philosophy: Architect vs. Engineer
Instead of asking an AI to "guess" numerical parameters (which LLMs are bad at), AEGIS splits the workload:
1.  **The Architect (Gemini):** Designs the *logic* of the strategy (indicators, entry/exit conditions) and creates a template with variables.
2.  **The Engineer (Genetic Algorithms):** Uses multi-objective optimization (NSGA-II) to mathematically find the optimal parameters for those variables.

```mermaid
graph TD
    subgraph "Cloud & Context"
        Gemini((Google Gemini)) 
        MarketData[Market Data (Binance)]
    end

    subgraph "AEGIS Brain (Raspberry Pi)"
        direction TB
        
        Context[Context Analysis] -->|Prompt| Architect[THE ARCHITECT<br>(Qualitative Logic)]
        Gemini <--> Architect
        
        Architect -->|Strategy Template| Engineer[THE ENGINEER<br>(Quantitative Optimization)]
        
        subgraph "Genetic Engineering"
            Engineer -->|NSGA-II| Backtester[Vectorized Backtester<br>(pandas/numpy)]
            Backtester -->|Profit / Drawdown| Engineer
        end
        
        Engineer -->|Optimized Strategy| Compiler[Compiler]
    end

    subgraph "Execution"
        Compiler -->|Hot Swap| Pilot[Freqtrade (The Pilot)]
        Pilot -->|Buy/Sell| Exchange((Exchange))
    end
```

### Key Components
1.  **The Pilot (Freqtrade):** Executes the final strategy deterministically, minute by minute.
2.  **The Architect (GenAI Module):** An AI agent that observes the market (Trend, Volatility) and writes *incomplete* Python code (templates) adapted to current weather.
3.  **The Engineer (Pymoo Module):** A genetic optimizer that runs thousands of fast simulations to fill the template's gaps with perfect numbers.
4.  **Vectorized Backtester:** An ultra-fast simulation engine written in `pandas` and `numpy` allowing 10,000 tests in minutes on a Raspberry Pi.

## 2. Hardware Setup (Raspberry Pi 4)

### Prerequisites
- Raspberry Pi 4 (8GB recommended for genetic compilation)
- SSD connected via USB 3.0 (Critical for data I/O)
- Raspberry Pi OS (64-bit)

### Optimization Steps
1.  **Enable ZRAM:** To optimize RAM usage during genetic evolution.
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
    ```

## 3. Deployment

### Automated Configuration
1.  **Clone and Setup:**
    ```bash
    git clone <repo_url> project_aegis
    cd project_aegis
    chmod +x scripts/setup_pi.sh
    sudo ./scripts/setup_pi.sh
    ```
    *Reboot your Pi after setup.*

2.  **Configuration:**
    - Copy `.env.example` to `.env` and fill in your `GEMINI_API_KEY`.
    - Ensure you have historical data downloaded in `freqtrade/user_data/data/binance`.

3.  **Launch:**
    ```bash
    docker-compose up -d --build
    ```
    *Note: The `--build` flag is necessary the first time to install new dependencies (pymoo, pandas).*

## 4. Neuro-Genetic Workflow
The system operates in a continuous loop (weekly default or manual trigger):

1.  **Analysis:** System detects "High Volatility, Bear Trend".
2.  **Design:** The Architect proposes: *"Use short RSI (period {x}) and Bollinger Band rejection (std {y})"*.
3.  **Evolution:** The Engineer tests populations of `{x}` and `{y}`.
    -   Gen 1: Mediocre result.
    -   Gen 10: Finds that `x=4` and `y=2.5` maximize profit and minimize risk.
4.  **Deployment:** `AEGIS_Strategy.py` is compiled and Freqtrade reloads the config automatically.

## 5. Project Structure

```
project_aegis/
├── aegis_brain/          # The Neuro-Genetic Brain
│   ├── modules/
│   │   ├── architect.py  # Designer (Gemini)
│   │   ├── engineer.py   # Optimizer (Pymoo)
│   │   └── backtester.py # Vectorized Engine
│   ├── strategy_evolver.py # Cycle Orchestrator
│   ├── brain.py          # Main Loop
│   └── requirements.txt  # pymoo, pandas, numpy, etc.
├── freqtrade/            # The Body (Execution)
│   └── user_data/
│       └── strategies/
│           └── AEGIS_Strategy.py # Final compiled result
├── mcp_wrapper/          # MCP Bridge (Optional in v3.0)
└── docker-compose.yml    # Orchestration
```

## 6. Security Notes
-   **No Numerical Hallucinations:** By using a mathematical optimizer for numbers, we eliminate the risk of the AI inventing losing parameters.
-   **Strict Validation:** The Engineer strictly penalizes strategies with few trades or excessive Drawdown.

---
*Generated by Antigravity for Project AEGIS*
