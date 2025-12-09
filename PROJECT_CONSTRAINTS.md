# 🚧 Project Constraints & Limits

Este archivo define las **Reglas de Oro** que todo agente o desarrollador debe respetar para mantener el proyecto operativo bajo el **Gemini Free Tier**.

## 1. Límites de API (Gemini Free) 📉
| Métrica | Límite | Estrategia de Mitigación |
| :--- | :--- | :--- |
| **Requests Per Day (RPD)** | **20** | El ciclo de `brain.py` debe correr cada **75 minutos** (4500s) mínimo. |
| **Requests Per Minute (RPM)** | **5** | Nunca paralelizar más de 2 agentes simultáneos. |
| **Tokens Per Minute (TPM)** | **250K** | Mantener prompts concisos. Evitar enviar logs masivos en una sola call. |

## 2. Configuración Obligatoria (`config.yaml`)
Cualquier cambio en la configuración debe validar que:
```yaml
cycle_interval: >= 4500  # 4500 segundos = 1.25 horas
```

## 3. Presupuesto de "Beast Mode"
Para las funciones avanzadas (War Room, Whale Watcher), no podemos hacer polling continuo.
*   **Estrategia:** Solo invocar a los agentes extra si el análisis técnico básico detecta una anomalía fuerte, o usar búsquedas manuales programadas una vez cada 4 horas.

---
> **IMPORTANTE:** Violar estos límites causará errores `429 Resource Exhausted` y detendrá el cerebro del bot.
