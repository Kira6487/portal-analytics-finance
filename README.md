# Analytics Finance SAP B1

Demo de portal analítico financiero para SAP Business One. La implementación
actual incluye diagnóstico, motor histórico, forecast, flujo de caja documental
y análisis predictivo detallado de CxC. Todavía no incluye frontend.

## Preparación local

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
```

En `cmd.exe`, la activación es:

```bat
.venv\Scripts\activate
```

La configuración se puede sobrescribir mediante `.env.local`, tomando
`.env.example` como referencia. Los valores por defecto son exclusivamente para
la demo local y **no deben almacenarse así en producción**.

## Pruebas y diagnóstico

Desde la raíz del repositorio:

```powershell
backend\.venv\Scripts\python backend\scripts\test_connection.py
backend\.venv\Scripts\python -m pytest backend\tests
```

## Endpoints

- `http://localhost:8000/api/diagnostics/health`
- `http://localhost:8000/api/diagnostics/sap-data`
- `http://localhost:8000/api/financial/metadata`
- `http://localhost:8000/api/financial/income-statement?year=2025`
- `http://localhost:8000/api/financial/income-statement-vs-budget?year=2025&basis_year=2024`
- `http://localhost:8000/api/financial/balance-summary?as_of_date=2025-12-23`
- `http://localhost:8000/api/financial/receivables/open`
- `http://localhost:8000/api/financial/payables/open`
- `http://localhost:8000/api/financial/cashflow/base?bucket=month`
- `http://localhost:8000/api/financial/profitability/dimensions?year=2025&dimension=OcrCode2`
- `http://localhost:8000/api/financial/budget/simulated?year=2025&basis_year=2024`
- `http://localhost:8000/api/forecasting/income-statement/dataset`
- `http://localhost:8000/api/forecasting/income-statement/backtest`
- `http://localhost:8000/api/forecasting/income-statement/forecast?horizon=6`
- `http://localhost:8000/api/forecasting/income-statement/executive-summary?horizon=6`
- `http://localhost:8000/api/cashflow-projection/payment-behavior`
- `http://localhost:8000/api/cashflow-projection/projectable-documents`
- `http://localhost:8000/api/cashflow-projection/weekly?horizon_weeks=13&scenario=base`
- `http://localhost:8000/api/cashflow-projection/weekly?horizon_weeks=13&scenario=base&opening_cash=1000000`
- `http://localhost:8000/api/cashflow-projection/scenarios?horizon_weeks=13&opening_cash=1000000`
- `http://localhost:8000/api/cashflow-projection/executive-summary?horizon_weeks=13&scenario=base`
- `http://localhost:8000/api/receivables-predictive/dataset`
- `http://localhost:8000/api/receivables-predictive/dataset?risk=high`
- `http://localhost:8000/api/receivables-predictive/customers?limit=20`
- `http://localhost:8000/api/receivables-predictive/priorities?limit=10`
- `http://localhost:8000/api/receivables-predictive/concentration`
- `http://localhost:8000/api/receivables-predictive/executive-summary`
- `http://localhost:8000/docs`

Todas las consultas son de solo lectura. La Fase 2 entrega estados históricos,
documentos abiertos, caja base, rentabilidad dimensional y presupuesto simulado.
La Fase 3 compara seis modelos mediante MAE, MAPE y RMSE y genera proyecciones a
3, 6 o 12 meses.
La Fase 4 combina documentos abiertos, comportamiento de pago, caja inicial,
escenarios y alertas en horizontes de 4, 8, 13 o 26 semanas.
La Fase 5 agrega score de riesgo, fecha de cobranza, prioridades y concentración
por factura y cliente.

## Moneda de reporte

La moneda oficial de la demo es `SOL`, mostrada como `S/`. Los importes usan
valores locales SAP. Los documentos fuente en otras monedas conservan su código
original y requieren validación FX para una versión productiva.

## Limitaciones conocidas

- La clasificación de cuentas de resultados es preliminar y requiere validación
  del equipo contable.
- El mapeo puede ajustarse en `backend/config/account_mapping_overrides.json`.
- OBGT y BGT1 existen, pero en la validación del 25 de junio de 2026 no tenían
  registros; la futura demo necesitará presupuesto simulado o una carga real.
- Se detectaron 80 meses de historia, aunque con alta volatilidad mensual.
- Los importes multimoneda requieren definir una moneda de reporte.
- El presupuesto es simulado y el mapeo contable continúa siendo preliminar.
- El forecast actual tiene confianza baja: MAPE 33.03% para ingresos y 30.29%
  para costo de ventas.
- Los asientos de cierre `TransType -3` se excluyen del dataset predictivo.
- La caja inicial automática se estima desde cuentas clase 10 y debe validarse
  con Tesorería; puede reemplazarse mediante `opening_cash`.
- La proyección no incluye líneas de crédito ni eventos aún no registrados.
- El score de CxC es una regla predictiva inicial, no una calificación crediticia.
- Ningún módulo modifica SAP ni automatiza acciones de cobranza.

Resultados: `docs/phase_1_diagnostics.md`,
`docs/phase_2_financial_base.md` y `docs/phase_3_income_forecasting.md`.
El flujo de caja se documenta en `docs/phase_4_cashflow_projection.md`.
CxC predictiva: `docs/phase_5_receivables_predictive.md`.

## Próxima fase sugerida

Fase 6: CxP predictiva y priorización de pagos, después de aprobar la política de
conversión a SOL.
