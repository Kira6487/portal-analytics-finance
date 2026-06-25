# Backend

API FastAPI de solo lectura para las Fases 1, 2 y 3 de Analytics Finance SAP B1.

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
