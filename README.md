# Analytics Finance SAP B1

Demo de portal analítico financiero para SAP Business One. La implementación actual
corresponde exclusivamente a la **Fase 1: conexión y diagnóstico de datos**. No
incluye todavía modelos predictivos ni frontend.

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
- `http://localhost:8000/docs`

La fase valida conexión, tablas principales de SAP B1, cobertura contable, CxC,
CxP, centros de costo/dimensiones, presupuesto y viabilidad predictiva inicial.
Todas las consultas son de solo lectura.

## Limitaciones conocidas

- La clasificación de cuentas de resultados es preliminar y requiere validación
  del equipo contable.
- OBGT y BGT1 existen, pero en la validación del 25 de junio de 2026 no tenían
  registros; la futura demo necesitará presupuesto simulado o una carga real.
- Se detectaron 80 meses de historia, aunque con alta volatilidad mensual.
- La viabilidad predictiva es una evaluación heurística; todavía no se entrenan
  modelos.

El resultado completo y las métricas reales están en
`docs/phase_1_diagnostics.md`.

## Próxima fase sugerida

Fase 2: construir el motor financiero histórico después de aprobar el mapeo del
plan de cuentas y revisar el diagnóstico de `docs/phase_1_diagnostics.md`.
