# Proyecto AEGIS: Sistema Híbrido Neuro-Genético (v3.0)

> **[Read in English](README_EN.md)**

**Proyecto AEGIS** es un sistema de trading avanzado diseñado para hardware de bajos recursos (ej. Raspberry Pi 4). Evolucionando más allá de la IA generativa simple, AEGIS v3.0 implementa una **Arquitectura Neuro-Genética** que separa la creatividad cualitativa de la optimización cuantitativa.

## 1. Resumen de la Arquitectura (v3.0)

### La Filosofía: Arquitecto vs. Ingeniero
En lugar de pedirle a una IA que "adivine" parámetros numéricos (lo cual hacen mal), AEGIS divide el trabajo:
1.  **El Arquitecto (Gemini):** Diseña la *lógica* de la estrategia (indicadores, condiciones de entrada/salida) y crea una plantilla con variables.
2.  **El Ingeniero (Algoritmos Genéticos):** Utiliza optimización multi-objetivo (NSGA-II) para encontrar matemáticamente los parámetros óptimos para esas variables.

```mermaid
graph TD
    subgraph "Nube & Contexto"
        Gemini((Google Gemini)) 
        MarketData[Datos de Mercado ((Binance))]
    end

    subgraph "AEGIS Brain (Raspberry Pi)"
        direction TB
        
        Context[Análisis de Contexto] -->|Prompt| Architect[EL ARQUITECTO<br>((Lógica Cualitativa))]
        Gemini <--> Architect
        
        Architect -->|Plantilla de Estrategia| Engineer[EL INGENIERO<br>((Optimización Cuantitativa))]
        
        subgraph "Ingeniería Genética"
            Engineer -->|NSGA-II| Backtester[Backtester Vectorizado<br>((pandas/numpy))]
            Backtester -->|Profit / Drawdown| Engineer
        end
        
        Engineer -->|Estrategia Optimizada| Compiler[Compilador]
    end

    subgraph "Ejecución"
        Compiler -->|Hot Swap| Pilot[Freqtrade ((El Piloto))]
        Pilot -->|Buy/Sell| Exchange((Exchange))
    end
```

### Componentes Clave
1.  **El Piloto (Freqtrade):** Ejecuta la estrategia final de manera determinista, minuto a minuto.
2.  **El Arquitecto (Módulo GenAI):** Un agente de IA que observa el mercado (Tendencia, Volatilidad) y escribe código Python *incompleto* (plantillas) adaptado al clima actual.
3.  **El Ingeniero (Módulo Pymoo):** Un optimizador genético que ejecuta miles de simulaciones rápidas para llenar los huecos de la plantilla con los números perfectos.
4.  **Backtester Vectorizado:** Un motor de simulación ultrarrápido escrito en `pandas` y `numpy` que permite correr 10,000 pruebas en minutos en una Raspberry Pi.

## 2. Configuración de Hardware (Raspberry Pi 4)

### Requisitos Previos
- Raspberry Pi 4 (8GB recomendada para compilación genética)
- SSD conectado vía USB 3.0 (Crítico para lectura de datos)
- Raspberry Pi OS (64-bit)

### Pasos de Optimización
1.  **Habilitar ZRAM:** Para optimizar el uso de memoria RAM durante la evolución genética.
    ```bash
    sudo apt install zram-tools
    echo "PERCENT=50" | sudo tee -a /etc/default/zramswap
    sudo service zramswap reload
    ```
2.  **Instalar Docker y Docker Compose:**
    ```bash
    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh get-docker.sh
    sudo usermod -aG docker $USER
    ```

## 3. Despliegue

### Configuración Automatizada
1.  **Clonar y Configurar:**
    ```bash
    git clone <repo_url> project_aegis
    cd project_aegis
    chmod +x scripts/setup_pi.sh
    sudo ./scripts/setup_pi.sh
    ```
    *Reinicia tu Pi después de la configuración.*

2.  **Configuración:**
    - Copia `.env.example` a `.env` y completa tu `GEMINI_API_KEY`.
    - Asegúrate de tener datos históricos descargados en `freqtrade/user_data/data/binance`.

3.  **Lanzamiento:**
    ```bash
    docker-compose up -d --build
    ```
    *Nota: El flag `--build` es necesario la primera vez para instalar las nuevas dependencias (pymoo, pandas).*

## 4. Flujo de Trabajo Neuro-Genético
El sistema opera en un ciclo continuo (por defecto semanal o manual):

1.  **Análisis:** El sistema detecta "Volatilidad Alta, Tendencia Bajista".
2.  **Diseño:** El Arquitecto propone: *"Usar RSI corto (periodo {x}) y rechazo de Bandas de Bollinger (std {y})"*.
3.  **Evolución:** El Ingeniero prueba poblaciones de `{x}` y `{y}`.
    -   Gen 1: Resultado mediocre.
    -   Gen 10: Encuentra que `x=4` y `y=2.5` maximizan ganancia y minimizan riesgo.
4.  **Despliegue:** Se compila `AEGIS_Strategy.py` y Freqtrade recarga la configuración automáticamente.

## 5. Estructura del Proyecto

```
project_aegis/
├── aegis_brain/          # El Cerebro Neuro-Genético
│   ├── modules/
│   │   ├── architect.py  # Diseñador (Gemini)
│   │   ├── engineer.py   # Optimizador (Pymoo)
│   │   └── backtester.py # Motor Vectorizado
│   ├── strategy_evolver.py # Orquestador del ciclo
│   ├── brain.py          # Bucle principal
│   └── requirements.txt  # pymoo, pandas, numpy, etc.
├── freqtrade/            # El Cuerpo (Ejecución)
│   └── user_data/
│       └── strategies/
│           └── AEGIS_Strategy.py # Resultado final compilado
├── mcp_wrapper/          # Puente MCP (Opcional en v3.0)
└── docker-compose.yml    # Orquestación
```

## 6. Notas de Seguridad
-   **Sin Alucinaciones Numéricas:** Al usar un optimizador matemático para los números, eliminamos el riesgo de que la IA invente parámeteros perdedores.
-   **Validación Estricta:** El Ingeniero penaliza duramente las estrategias con pocas operaciones o Drawdown excesivo.

---
*Generado por Antigravity para Proyecto AEGIS*
