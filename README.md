# Analytics Finance SAP B1

Demo de portal analítico financiero para SAP Business One. La implementación
actual incluye la **Fase 1 de diagnóstico** y la **Fase 2 del motor financiero
histórico**. Todavía no incluye modelos predictivos ni frontend.

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
- `http://localhost:8000/docs`

Todas las consultas son de solo lectura. La Fase 2 entrega estados históricos,
documentos abiertos, caja base, rentabilidad dimensional y presupuesto simulado.

## Limitaciones conocidas

- La clasificación de cuentas de resultados es preliminar y requiere validación
  del equipo contable.
- El mapeo puede ajustarse en `backend/config/account_mapping_overrides.json`.
- OBGT y BGT1 existen, pero en la validación del 25 de junio de 2026 no tenían
  registros; la futura demo necesitará presupuesto simulado o una carga real.
- Se detectaron 80 meses de historia, aunque con alta volatilidad mensual.
- Los importes multimoneda requieren definir una moneda de reporte.
- Todavía no se entrenan modelos.

Resultados: `docs/phase_1_diagnostics.md` y `docs/phase_2_financial_base.md`.

## Próxima fase sugerida

Fase 3: validar el mapeo con Contabilidad y construir el primer forecast mensual
de ingresos y margen bruto con backtesting explicable.
