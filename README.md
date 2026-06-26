# Analytics Finance SAP B1

Demo de portal analitico financiero para SAP Business One. La implementacion
actual incluye diagnostico, motor historico, forecast, flujo de caja documental,
CxC predictiva, CxP predictiva y Balance proyectado simplificado. Todavia no
incluye frontend.

## Preparacion local

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
```

En `cmd.exe`, la activacion es:

```bat
.venv\Scripts\activate
```

La configuracion se puede sobrescribir mediante `.env.local`, tomando
`.env.example` como referencia. Los valores por defecto son exclusivamente para
la demo local y no deben almacenarse asi en produccion.

## Pruebas y diagnostico

Desde la raiz del repositorio:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend\tests
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
- `http://localhost:8000/api/payables-predictive/dataset`
- `http://localhost:8000/api/payables-predictive/dataset?priority=urgent`
- `http://localhost:8000/api/payables-predictive/dataset?risk=high`
- `http://localhost:8000/api/payables-predictive/dataset?scenario=pessimistic`
- `http://localhost:8000/api/payables-predictive/vendors?limit=20`
- `http://localhost:8000/api/payables-predictive/priorities?limit=10`
- `http://localhost:8000/api/payables-predictive/deferrable?limit=10`
- `http://localhost:8000/api/payables-predictive/concentration`
- `http://localhost:8000/api/payables-predictive/executive-summary`
- `http://localhost:8000/api/balance-projection/dataset`
- `http://localhost:8000/api/balance-projection/weekly?horizon_weeks=13&scenario=base`
- `http://localhost:8000/api/balance-projection/weekly?horizon_weeks=13&scenario=base&opening_cash=1000000`
- `http://localhost:8000/api/balance-projection/scenarios?horizon_weeks=13&opening_cash=1000000`
- `http://localhost:8000/api/balance-projection/drivers?horizon_weeks=13&scenario=base`
- `http://localhost:8000/api/balance-projection/executive-summary?horizon_weeks=13&scenario=base`
- `http://localhost:8000/docs`

Todas las consultas son de solo lectura. La Fase 2 entrega estados historicos,
documentos abiertos, caja base, rentabilidad dimensional y presupuesto simulado.
La Fase 3 compara seis modelos mediante MAE, MAPE y RMSE y genera proyecciones a
3, 6 o 12 meses. La Fase 4 combina documentos abiertos, comportamiento de pago,
caja inicial, escenarios y alertas. La Fase 5 agrega CxC predictiva por factura
y cliente. La Fase 6 agrega CxP predictiva, prioridad de pago, riesgo
operativo/financiero, proveedores por presion de caja, pagos revisables y
concentracion. La Fase 7 agrega Balance proyectado simplificado, posicion
financiera futura, ratios, escenarios, drivers y resumen ejecutivo gerencial.

## Moneda de reporte

La moneda oficial de la demo es `SOL`, mostrada como `S/`. Los importes usan
valores locales SAP. Los documentos fuente en otras monedas conservan su codigo
original y requieren validacion FX para una version productiva.

Las recomendaciones de CxP son gerenciales: no modifican SAP, no programan
pagos automaticamente, no envian correos y no reemplazan el criterio de
Tesoreria ni Contabilidad.

El Balance proyectado de Fase 7 tambien es gerencial: no reemplaza el Balance
oficial de SAP, no crea asientos contables y depende de supuestos de cobranza,
pagos y forecast.

## Limitaciones conocidas

- La clasificacion de cuentas de resultados es preliminar y requiere validacion
  del equipo contable.
- El mapeo puede ajustarse en `backend/config/account_mapping_overrides.json`.
- OBGT y BGT1 existen, pero en la validacion del 25 de junio de 2026 no tenian
  registros; la futura demo necesitara presupuesto simulado o una carga real.
- Se detectaron 80 meses de historia, aunque con alta volatilidad mensual.
- Los importes multimoneda usan SOL como moneda oficial de demo, pero requieren
  politica FX productiva antes de produccion.
- El presupuesto es simulado y el mapeo contable continua siendo preliminar.
- El forecast actual tiene confianza baja: MAPE 33.03% para ingresos y 30.29%
  para costo de ventas.
- Los asientos de cierre `TransType -3` se excluyen del dataset predictivo.
- La caja inicial automatica se estima desde cuentas clase 10 y debe validarse
  con Tesoreria; puede reemplazarse mediante `opening_cash`.
- La proyeccion no incluye lineas de credito ni eventos aun no registrados.
- El score de CxC es una regla predictiva inicial, no una calificacion
  crediticia.
- El score de CxP es una regla gerencial inicial, no una instruccion automatica
  de pago.
- La fecha recomendada de CxP no programa pagos ni modifica documentos SAP.
- Ningun modulo modifica SAP ni automatiza acciones de cobranza o pago.
- La conexion SQL/ODBC actual puede fallar por cifrado/conectividad; los
  endpoints devuelven warnings controlados y no inventan saldos SAP.

## Documentacion de fases

- `docs/phase_1_diagnostics.md`
- `docs/phase_2_financial_base.md`
- `docs/phase_3_income_forecasting.md`
- `docs/phase_4_cashflow_projection.md`
- `docs/phase_5_receivables_predictive.md`
- `docs/phase_6_payables_predictive.md`
- `docs/phase_7_balance_projection.md`

## Proxima fase sugerida

Fase 8: resolver conectividad SQL/ODBC y validar caja inicial antes de avanzar a
frontend final, rentabilidad predictiva por dimensiones o automatizaciones.
