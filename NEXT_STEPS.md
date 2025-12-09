# 🚀 Project AEGIS: Next Steps Roadmap

Ahora que el MVP ("Project Genesis") está operativo, aquí tienes la hoja de ruta para llevar a AEGIS al nivel "Beast Mode".

## 1. Fase de Validación Real (Prioridad Alta) 🎯
Actualmente, el `EvolutionManager` genera estrategias, pero el paso de **validación (backtesting)** está simulado para estabilidad.
- [ ] **Implementar Parsing Real:** Modificar `strategy_evolver.py` para leer la salida JSON real de `freqtrade backtesting`.
- [ ] **Definir KPIs de Aceptación:** Establecer reglas estrictas (ej. Profit > 5%, Drawdown < 10%) para que una estrategia sea promovida automáticamente.
- [ ] **Prueba de Fuego:** Ejecutar una evolución completa donde AEGIS detecte una mejora real y reemplace la estrategia sin intervención humana.

## 2. Automatización y Robustez ⚙️
- [ ] **Cron Jobs Reales:** Verificar que el scheduler interno (`sunday 02:00 utc`) funcione en el entorno Docker de larga duración.
- [ ] **Persistencia:** Configurar una base de datos PostgreSQL en lugar de SQLite para manejar gigabytes de historia de trading.
- [ ] **Notificaciones:** Conectar `brain.py` con Telegram para que AEGIS te avise: *"He creado una nueva estrategia v2.1. ¿La despliego?"*.

## 3. "Beast Mode" (Edición "Zero Cost") 🦁💸
Optimización para usar recursos gratuitos y la inteligencia de Gemini:
- [ ] **War Room (Multi-Agente):** Crear agentes especializados (Bull, Bear, Risk) usando *el mismo modelo* Gemini existente (sin costo extra).
- [ ] **Whale Watcher (OSINT):** En lugar de APIs pagas, instruiremos a Gemini para que busque *"Large Bitcoin transfers last 24h"* en agregadores públicos y noticias.
- [ ] **Sentiment Sniper (Google Grounding):** Usar la herramienta de búsqueda de Gemini para escanear *sentimiento en Reddit y X* mediante Google Search (Gratis en el tier actual).

## 4. Guía de Operación Diaria 🛠️
Mientras desarrollamos lo anterior, mantén esta rutina:
1.  **Monitoreo:** Revisa logs cada 24h (`docker logs aegis_strategist`).
2.  **Evolución Manual:** Ejecuta `execution_manager.py` los domingos si no quieres esperar al automático.
3.  **Backups:** Guarda copias de tus estrategias ganadoras (`user_data/strategies`).

---
> **Nota:** El sistema actual ya es funcional para trading asistido por IA (Análisis Macro). Los pasos anteriores son para alcanzar la **Autonomía Total**.
