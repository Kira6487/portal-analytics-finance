# Backend

API FastAPI de solo lectura para las Fases 1 a 4 de Analytics Finance SAP B1.

Desde esta carpeta:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
```

El script de diagnóstico se ejecuta desde la raíz del repositorio:

```powershell
python backend/scripts/test_connection.py
```

Los endpoints financieros se documentan en `/docs` y en
`docs/phase_2_financial_base.md`.

Backtesting y forecast:

```powershell
Invoke-RestMethod http://localhost:8000/api/forecasting/income-statement/backtest
Invoke-RestMethod "http://localhost:8000/api/forecasting/income-statement/forecast?horizon=6"
```

El detalle de modelos y métricas está en
`docs/phase_3_income_forecasting.md`.

Proyección de caja:

```powershell
Invoke-RestMethod "http://localhost:8000/api/cashflow-projection/weekly?horizon_weeks=13&scenario=base&opening_cash=1000000"
Invoke-RestMethod "http://localhost:8000/api/cashflow-projection/scenarios?horizon_weeks=13&opening_cash=1000000"
```

Detalles: `docs/phase_4_cashflow_projection.md`.
